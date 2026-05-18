"""DataUpdateCoordinator for PocketSmith."""
import asyncio
import calendar
import logging
from datetime import date

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

_API_BASE = "https://api.pocketsmith.com/v2"
_REQUEST_TIMEOUT = 10
_MAX_RETRY_AFTER = 300  # Never sleep more than 5 minutes on a 429


def _parse_link_next(link_header: str):
    """Extract the rel="next" URL from a Link header string, or return None."""
    for part in link_header.split(","):
        if 'rel="next"' in part:
            start = part.find("<")
            end = part.find(">")
            if start != -1 and end != -1:
                return part[start + 1:end]
    return None


async def _raise_for_api_error(response: aiohttp.ClientResponse, context: str) -> None:
    """Raise the appropriate exception for a non-2xx PocketSmith API response."""
    if response.status == 400:
        try:
            error_body = (await response.json()).get("error", "unknown error")
        except Exception:
            error_body = "unknown error"
        raise UpdateFailed(
            "PocketSmith returned a bad request error fetching %s: %s" % (context, error_body)
        )
    if response.status == 401:
        raise ConfigEntryAuthFailed("PocketSmith developer key is invalid or has been revoked")
    if response.status == 403:
        raise UpdateFailed(
            "PocketSmith access denied fetching %s — developer key lacks required permissions" % context
        )
    if response.status == 404:
        raise UpdateFailed(
            "PocketSmith could not find %s data — this may be a temporary API issue" % context
        )
    if response.status == 405:
        raise UpdateFailed(
            "PocketSmith returned Method Not Allowed (HTTP 405) fetching %s — please report this bug" % context
        )
    if response.status == 429:
        retry_after_raw = response.headers.get("Retry-After", "")
        try:
            retry_after = min(float(retry_after_raw), _MAX_RETRY_AFTER)
        except (ValueError, TypeError):
            retry_after = 60.0
        _LOGGER.warning(
            "PocketSmith rate limit hit fetching %s — sleeping %ss before failing update",
            context, retry_after,
        )
        await asyncio.sleep(retry_after)
        raise UpdateFailed(
            "PocketSmith API rate limit exceeded fetching %s — will retry on next update" % context
        )
    if response.status == 503:
        raise UpdateFailed(
            "PocketSmith is temporarily unavailable (HTTP 503) — will retry on next update"
        )
    if response.status >= 500:
        raise UpdateFailed(
            "PocketSmith server error (HTTP %s) fetching %s — will retry when service recovers"
            % (response.status, context)
        )
    response.raise_for_status()


class PocketSmithCoordinator(DataUpdateCoordinator):
    """Fetch all PocketSmith data in a single coordinated update."""

    def __init__(self, hass: HomeAssistant, developer_key: str, update_interval, entry: ConfigEntry) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
            config_entry=entry,
        )
        self._developer_key = developer_key
        self._entry = entry
        self._headers = {
            "Accept": "application/json",
            "Authorization": "Key %s" % developer_key,
        }
        # Limit to one in-flight request at a time to avoid burst rate limiting.
        self._request_semaphore = asyncio.Semaphore(1)

    async def _get(self, session: aiohttp.ClientSession, url: str, context: str):
        """Make a rate-limited GET request and return the parsed JSON response and Link header."""
        async with self._request_semaphore:
            async with asyncio.timeout(_REQUEST_TIMEOUT):
                async with session.get(url, headers=self._headers) as response:
                    await _raise_for_api_error(response, context)
                    data = await response.json()
                    link = response.headers.get("Link", "")
        return data, link

    async def _async_update_data(self) -> dict:
        """Fetch user, accounts, and uncategorised transaction count."""
        session = async_get_clientsession(self.hass)

        try:
            user_id, user = await self._fetch_user_id(session)
            accounts = await self._fetch_accounts(session, user_id)
            uncategorised_count = await self._fetch_uncategorised_count(session, user_id)
            categories = await self._fetch_categories(session, user_id)
            budget = await self._fetch_budget(session, user_id)
            monthly_transactions, monthly_transaction_counts = await self._fetch_monthly_transactions(session, user_id)
            monthly_events = await self._fetch_monthly_events(session, user_id)
        except aiohttp.ClientError as err:
            raise UpdateFailed(
                "Unable to reach the PocketSmith API. Check your network connection."
            ) from err
        except asyncio.TimeoutError as err:
            raise UpdateFailed(
                "PocketSmith API request timed out. Check your network connection."
            ) from err

        enriched_categories = self._build_enriched_categories(categories, budget, monthly_transactions, monthly_events, monthly_transaction_counts)

        return {
            "user_id": user_id,
            "user": user,
            "accounts": accounts,
            "uncategorised_count": uncategorised_count,
            "categories": categories,
            "budget": budget,
            "monthly_transactions": monthly_transactions,
            "monthly_transaction_counts": monthly_transaction_counts,
            "monthly_events": monthly_events,
            "enriched_categories": enriched_categories,
            "forecast_last_updated": dt_util.utcnow(),
        }

    async def _fetch_user_id(self, session: aiohttp.ClientSession) -> int:
        """Return the authenticated user's ID."""
        url = "%s/me" % _API_BASE
        data, _ = await self._get(session, url, "user profile")

        user_id = data.get("id")
        if user_id is None:
            raise UpdateFailed(
                "Received an unexpected response from PocketSmith — the user profile was missing a required field. "
                "This may be a temporary API issue."
            )

        _LOGGER.debug("Fetched user ID: %s", user_id)
        return user_id, data

    async def _fetch_accounts(self, session: aiohttp.ClientSession, user_id: int) -> list:
        """Return all accounts for the given user."""
        url = "%s/users/%s/accounts" % (_API_BASE, user_id)
        accounts, _ = await self._get(session, url, "accounts")
        _LOGGER.debug("Fetched %s accounts for user %s", len(accounts), user_id)
        return accounts

    async def _fetch_uncategorised_count(self, session: aiohttp.ClientSession, user_id: int) -> int:
        """Return the count of transactions with no category across all pages."""
        base_url = "%s/users/%s/transactions" % (_API_BASE, user_id)
        count = 0
        url = "%s?uncategorised=1&per_page=1000" % base_url

        while url:
            transactions, link = await self._get(session, url, "uncategorised transactions")
            if not transactions:
                break
            count += sum(1 for t in transactions if t.get("category") is None)
            _LOGGER.debug("Fetched %s transactions for this page", len(transactions))
            url = _parse_link_next(link)

        _LOGGER.debug("Total uncategorised transactions for user %s: %s", user_id, count)
        return count

    async def _fetch_categories(self, session: aiohttp.ClientSession, user_id: int) -> list:
        """Return all categories for the given user."""
        url = "%s/users/%s/categories?per_page=1000" % (_API_BASE, user_id)
        categories = []

        while url:
            page_categories, link = await self._get(session, url, "categories")
            categories.extend(page_categories)
            url = _parse_link_next(link)

        _LOGGER.debug("Fetched %s categories for user %s", len(categories), user_id)
        return categories

    async def _fetch_budget(self, session: aiohttp.ClientSession, user_id: int) -> list:
        """Return budget data for the given user."""
        url = "%s/users/%s/budget?per_page=1000" % (_API_BASE, user_id)
        budget = []

        while url:
            page_budget, link = await self._get(session, url, "budget")
            budget.extend(page_budget)
            url = _parse_link_next(link)

        _LOGGER.debug("Fetched budget for user %s", user_id)
        return budget

    async def _fetch_monthly_transactions(self, session: aiohttp.ClientSession, user_id: int) -> tuple[dict, dict]:
        """Return actual spend totals and transaction counts grouped by category ID for the current month."""
        today = dt_util.now().date()
        start_date = date(today.year, today.month, 1).isoformat()
        last_day = calendar.monthrange(today.year, today.month)[1]
        end_date = date(today.year, today.month, last_day).isoformat()

        _LOGGER.debug(
            "Fetching monthly transactions for user %s (%s to %s)",
            user_id, start_date, end_date,
        )

        base_url = "%s/users/%s/transactions" % (_API_BASE, user_id)
        url = "%s?start_date=%s&end_date=%s&per_page=1000" % (base_url, start_date, end_date)
        totals: dict[int, float] = {}
        counts: dict[int, int] = {}
        transaction_count = 0

        while url:
            transactions, link = await self._get(session, url, "monthly transactions")
            if not transactions:
                break

            for t in transactions:
                category = t.get("category")
                if category is None:
                    continue
                cat_id = category.get("id")
                amount = t.get("amount", 0)
                totals[cat_id] = totals.get(cat_id, 0) + abs(amount)
                counts[cat_id] = counts.get(cat_id, 0) + 1
                transaction_count += 1

            url = _parse_link_next(link)

        _LOGGER.debug(
            "Fetched %s monthly transactions across %s categories for user %s",
            transaction_count, len(totals), user_id,
        )
        return totals, counts

    async def _fetch_monthly_events(self, session: aiohttp.ClientSession, user_id: int) -> dict:
        """Return budgeted amount totals grouped by category ID for the current month."""
        today = dt_util.now().date()
        start_date = date(today.year, today.month, 1).isoformat()
        last_day = calendar.monthrange(today.year, today.month)[1]
        end_date = date(today.year, today.month, last_day).isoformat()

        _LOGGER.debug(
            "Fetching monthly events for user %s (%s to %s)",
            user_id, start_date, end_date,
        )

        url = "%s/users/%s/events?start_date=%s&end_date=%s&per_page=1000" % (_API_BASE, user_id, start_date, end_date)

        totals: dict[int, float] = {}
        event_count = 0

        while url:
            events, link = await self._get(session, url, "monthly events")
            if not events:
                break

            for e in events:
                category = e.get("category")
                if category is None:
                    continue
                cat_id = category.get("id")
                amount = e.get("amount", 0)
                totals[cat_id] = totals.get(cat_id, 0) + abs(amount)
                event_count += 1

            url = _parse_link_next(link)

        _LOGGER.debug(
            "Fetched %s monthly events across %s categories for user %s. Category IDs with events: %s",
            event_count, len(totals), user_id, sorted(totals.keys()),
        )
        return totals

    def _build_enriched_categories(self, categories: list, budget: list, monthly_transactions: dict, monthly_events: dict, monthly_transaction_counts: dict) -> list:
        """Return a flat enriched list of all categories with monthly budget data.

        For each non-transfer category:
        - actual: sourced from monthly_transactions (sum of real transactions this calendar month)
        - budgeted (non-bill categories): pro-rated from the budget API's forecast_amount to the current month
          Formula: abs(forecast_amount) / period_days * days_in_current_month, summed across all budget packages
        - budgeted (bill categories): sourced from monthly_events (sum of scheduled events this calendar month)
        """

        def _flatten(cats, flat):
            for cat in cats:
                flat[cat["id"]] = cat
                _flatten(cat.get("children") or [], flat)

        flat_cats = {}
        _flatten(categories, flat_cats)

        budget_by_category = {}
        for pkg in budget:
            if not isinstance(pkg, dict):
                continue
            cat = pkg.get("category")
            if cat:
                budget_by_category.setdefault(cat["id"], []).append(pkg)

        today = dt_util.now().date()
        days_in_month = calendar.monthrange(today.year, today.month)[1]

        result = []
        for cat_id, cat in flat_cats.items():
            if cat.get("is_transfer"):
                continue
            parent_id = cat.get("parent_id")
            parent_title = flat_cats[parent_id]["title"] if parent_id and parent_id in flat_cats else None

            budgeted = None
            actual = None
            remaining = None
            over_by = None
            over_budget = False
            percentage_used = None
            currency = "AUD"

            actual = monthly_transactions.get(cat_id)

            if actual is None and cat_id in budget_by_category:
                actual = 0

            if cat.get("is_bill"):
                budgeted = monthly_events.get(cat_id)
                if budgeted is None:
                    _LOGGER.debug(
                        "Bill category '%s' (id=%s) has no event in current month. "
                        "Event category IDs available: %s",
                        cat.get("title"), cat_id, sorted(monthly_events.keys()),
                    )
            else:
                pkgs = budget_by_category.get(cat_id, [])
                if not pkgs:
                    _LOGGER.debug(
                        "Category '%s' (id=%s) has no budget packages",
                        cat.get("title"), cat_id,
                    )
                for pkg in pkgs:
                    analysis = pkg.get("expense") or pkg.get("income")
                    if not analysis:
                        _LOGGER.debug(
                            "Category '%s' (id=%s) budget package has no expense/income data",
                            cat.get("title"), cat_id,
                        )
                        continue
                    currency = analysis.get("currency_code", "AUD").upper()
                    current_period = next(
                        (p for p in analysis.get("periods", []) if p.get("current")),
                        None,
                    )
                    if not current_period:
                        period_dates = [(p.get("start_date"), p.get("end_date")) for p in analysis.get("periods", [])]
                        _LOGGER.debug(
                            "Category '%s' (id=%s) has %d budget package(s) but no current period. "
                            "Available periods: %s",
                            cat.get("title"), cat_id, len(pkgs), period_dates,
                        )
                        continue
                    fc = current_period.get("forecast_amount")
                    if fc is None:
                        continue
                    try:
                        p_start = date.fromisoformat(current_period["start_date"])
                        p_end = date.fromisoformat(current_period["end_date"])
                        period_days = (p_end - p_start).days + 1
                    except (KeyError, ValueError, TypeError):
                        continue
                    if period_days <= 0:
                        continue
                    budgeted = (budgeted or 0) + abs(fc) / period_days * days_in_month

            if cat.get("is_bill"):
                for pkg in budget_by_category.get(cat_id, []):
                    analysis = pkg.get("expense") or pkg.get("income")
                    if analysis:
                        currency = analysis.get("currency_code", "AUD").upper()
                        break

            if budgeted is not None:
                budgeted = round(budgeted, 2)

            if budgeted is not None or actual is not None:
                b = budgeted or 0
                a = actual or 0
                over_budget = a > b
                over_by = a - b if over_budget else 0
                remaining = b - a if not over_budget else 0
                percentage_used = round(a / b * 100, 2) if b > 0 else None

            result.append({
                "category_id": cat_id,
                "category_title": cat.get("title"),
                "parent_id": parent_id,
                "parent_title": parent_title,
                "is_bill": cat.get("is_bill"),
                "is_transfer": cat.get("is_transfer"),
                "budgeted": budgeted,
                "actual": actual,
                "remaining": remaining,
                "over_by": over_by,
                "over_budget": over_budget,
                "percentage_used": percentage_used,
                "currency": currency,
                "transaction_count": monthly_transaction_counts.get(cat_id, 0),
            })

        return result
