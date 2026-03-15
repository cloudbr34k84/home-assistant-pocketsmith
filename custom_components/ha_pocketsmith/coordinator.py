"""DataUpdateCoordinator for PocketSmith."""
import asyncio
import logging
from datetime import date, timedelta

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, CONF_PERIOD, CONF_INTERVAL, DEFAULT_PERIOD, DEFAULT_INTERVAL

_LOGGER = logging.getLogger(__name__)

_API_BASE = "https://api.pocketsmith.com/v2"
_REQUEST_TIMEOUT = 10


def _parse_link_next(link_header: str):
    """Extract the rel="next" URL from a Link header string, or return None."""
    for part in link_header.split(","):
        if 'rel="next"' in part:
            start = part.find("<")
            end = part.find(">")
            if start != -1 and end != -1:
                return part[start + 1:end]
    return None


class PocketSmithCoordinator(DataUpdateCoordinator):
    """Fetch all PocketSmith data in a single coordinated update."""

    def __init__(self, hass: HomeAssistant, developer_key: str, update_interval, entry: ConfigEntry) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self._developer_key = developer_key
        self._entry = entry
        self._headers = {
            "Accept": "application/json",
            "Authorization": "Key %s" % developer_key,
        }

    async def _async_update_data(self) -> dict:
        """Fetch user, accounts, and uncategorised transaction count."""
        session = async_get_clientsession(self.hass)

        try:
            user_id = await self._fetch_user_id(session)
            accounts = await self._fetch_accounts(session, user_id)
            uncategorised_count = await self._fetch_uncategorised_count(session, user_id)
            categories = await self._fetch_categories(session, user_id)
            budget = await self._fetch_budget(session, user_id)
            budget_summary = await self._fetch_budget_summary(session, user_id)
            trend_analysis = await self._fetch_trend_analysis(session, user_id, categories, accounts)
        except aiohttp.ClientError as err:
            raise UpdateFailed(
                "Unable to reach the PocketSmith API. Check your network connection."
            ) from err
        except asyncio.TimeoutError as err:
            raise UpdateFailed(
                "PocketSmith API request timed out. Check your network connection."
            ) from err

        enriched_categories = self._build_enriched_categories(categories, budget, trend_analysis)

        return {
            "user_id": user_id,
            "accounts": accounts,
            "uncategorised_count": uncategorised_count,
            "categories": categories,
            "budget": budget,
            "budget_summary": budget_summary,
            "trend_analysis": trend_analysis,
            "enriched_categories": enriched_categories,
        }

    async def _fetch_user_id(self, session: aiohttp.ClientSession) -> int:
        """Return the authenticated user's ID."""
        url = "%s/me" % _API_BASE

        async with asyncio.timeout(_REQUEST_TIMEOUT):
            async with session.get(url, headers=self._headers) as response:
                if response.status == 400:
                    try:
                        error_body = (await response.json()).get("error", "unknown error")
                    except Exception:
                        error_body = "unknown error"
                    raise UpdateFailed(
                        "PocketSmith returned a bad request error: %s. This may indicate a bug in the integration." % error_body
                    )
                if response.status == 401:
                    raise UpdateFailed(
                        "PocketSmith authentication failed — your developer key is invalid or has been revoked. "
                        "Reconfigure the integration to fix this."
                    )
                if response.status == 403:
                    raise UpdateFailed(
                        "PocketSmith access denied — your developer key lacks the required permissions "
                        "to read your account data."
                    )
                if response.status == 405:
                    raise UpdateFailed(
                        "PocketSmith returned Method Not Allowed (HTTP 405). This is likely a bug in the integration — please report it."
                    )
                if response.status == 429:
                    raise UpdateFailed(
                        "PocketSmith API rate limit exceeded. The integration will retry on the next update."
                    )
                if response.status == 503:
                    raise UpdateFailed(
                        "PocketSmith is temporarily unavailable for maintenance (HTTP 503). The integration will retry on the next update."
                    )
                if response.status >= 500:
                    raise UpdateFailed(
                        "PocketSmith is experiencing server issues (HTTP %s). "
                        "Data will refresh when the service recovers." % response.status
                    )
                response.raise_for_status()
                data = await response.json()

        user_id = data.get("id")
        if user_id is None:
            raise UpdateFailed(
                "Received an unexpected response from PocketSmith — the user profile was missing a required field. "
                "This may be a temporary API issue."
            )

        _LOGGER.debug("Fetched user ID: %s", user_id)
        return user_id

    async def _fetch_accounts(self, session: aiohttp.ClientSession, user_id: int) -> list:
        """Return all accounts for the given user."""
        url = "%s/users/%s/accounts" % (_API_BASE, user_id)

        async with asyncio.timeout(_REQUEST_TIMEOUT):
            async with session.get(url, headers=self._headers) as response:
                if response.status == 400:
                    try:
                        error_body = (await response.json()).get("error", "unknown error")
                    except Exception:
                        error_body = "unknown error"
                    raise UpdateFailed(
                        "PocketSmith returned a bad request error: %s. This may indicate a bug in the integration." % error_body
                    )
                if response.status == 401:
                    raise UpdateFailed(
                        "PocketSmith authentication failed — your developer key is invalid or has been revoked. "
                        "Reconfigure the integration to fix this."
                    )
                if response.status == 403:
                    raise UpdateFailed(
                        "PocketSmith access denied — your developer key lacks the required permissions "
                        "to read your accounts."
                    )
                if response.status == 404:
                    raise UpdateFailed(
                        "PocketSmith could not find your account data. This may be a temporary API issue."
                    )
                if response.status == 405:
                    raise UpdateFailed(
                        "PocketSmith returned Method Not Allowed (HTTP 405). This is likely a bug in the integration — please report it."
                    )
                if response.status == 429:
                    raise UpdateFailed(
                        "PocketSmith API rate limit exceeded. The integration will retry on the next update."
                    )
                if response.status == 503:
                    raise UpdateFailed(
                        "PocketSmith is temporarily unavailable for maintenance (HTTP 503). The integration will retry on the next update."
                    )
                if response.status >= 500:
                    raise UpdateFailed(
                        "PocketSmith is experiencing server issues (HTTP %s). "
                        "Data will refresh when the service recovers." % response.status
                    )
                response.raise_for_status()
                accounts = await response.json()

        _LOGGER.debug("Fetched %s accounts for user %s", len(accounts), user_id)
        return accounts

    async def _fetch_uncategorised_count(self, session: aiohttp.ClientSession, user_id: int) -> int:
        """Return the count of transactions with no category across all pages."""
        base_url = "%s/users/%s/transactions" % (_API_BASE, user_id)
        count = 0
        url = "%s?uncategorised=1&per_page=1000" % base_url

        while url:
            next_url = None

            async with asyncio.timeout(_REQUEST_TIMEOUT):
                async with session.get(url, headers=self._headers) as response:
                    if response.status == 400:
                        try:
                            error_body = (await response.json()).get("error", "unknown error")
                        except Exception:
                            error_body = "unknown error"
                        raise UpdateFailed(
                            "PocketSmith returned a bad request error: %s. This may indicate a bug in the integration." % error_body
                        )
                    if response.status == 401:
                        raise UpdateFailed(
                            "PocketSmith authentication failed — your developer key is invalid or has been revoked. "
                            "Reconfigure the integration to fix this."
                        )
                    if response.status == 403:
                        raise UpdateFailed(
                            "PocketSmith access denied — your developer key lacks the required permissions "
                            "to read your transactions."
                        )
                    if response.status == 404:
                        raise UpdateFailed(
                            "PocketSmith could not find your transaction data. This may be a temporary API issue."
                        )
                    if response.status == 405:
                        raise UpdateFailed(
                            "PocketSmith returned Method Not Allowed (HTTP 405). This is likely a bug in the integration — please report it."
                        )
                    if response.status == 429:
                        raise UpdateFailed(
                            "PocketSmith API rate limit exceeded. The integration will retry on the next update."
                        )
                    if response.status == 503:
                        raise UpdateFailed(
                            "PocketSmith is temporarily unavailable for maintenance (HTTP 503). The integration will retry on the next update."
                        )
                    if response.status >= 500:
                        raise UpdateFailed(
                            "PocketSmith is experiencing server issues (HTTP %s). "
                            "Data will refresh when the service recovers." % response.status
                        )
                    response.raise_for_status()
                    transactions = await response.json()
                    next_url = _parse_link_next(response.headers.get("Link", ""))

            if not transactions:
                break

            count += sum(1 for t in transactions if t.get("category") is None)
            _LOGGER.debug("Fetched %s transactions for this page", len(transactions))
            url = next_url

        _LOGGER.debug("Total uncategorised transactions for user %s: %s", user_id, count)
        return count

    async def _fetch_categories(self, session: aiohttp.ClientSession, user_id: int) -> list:
        """Return all categories for the given user."""
        url = "%s/users/%s/categories?per_page=1000" % (_API_BASE, user_id)
        categories = []

        while url:
            next_url = None

            async with asyncio.timeout(_REQUEST_TIMEOUT):
                async with session.get(url, headers=self._headers) as response:
                    if response.status == 400:
                        try:
                            error_body = (await response.json()).get("error", "unknown error")
                        except Exception:
                            error_body = "unknown error"
                        raise UpdateFailed(
                            "PocketSmith returned a bad request error: %s. This may indicate a bug in the integration." % error_body
                        )
                    if response.status == 401:
                        raise UpdateFailed(
                            "PocketSmith authentication failed — your developer key is invalid or has been revoked. "
                            "Reconfigure the integration to fix this."
                        )
                    if response.status == 403:
                        raise UpdateFailed(
                            "PocketSmith access denied — your developer key lacks the required permissions "
                            "to read your categories."
                        )
                    if response.status == 404:
                        raise UpdateFailed(
                            "PocketSmith could not find your category data. This may be a temporary API issue."
                        )
                    if response.status == 405:
                        raise UpdateFailed(
                            "PocketSmith returned Method Not Allowed (HTTP 405). This is likely a bug in the integration — please report it."
                        )
                    if response.status == 429:
                        raise UpdateFailed(
                            "PocketSmith API rate limit exceeded. The integration will retry on the next update."
                        )
                    if response.status == 503:
                        raise UpdateFailed(
                            "PocketSmith is temporarily unavailable for maintenance (HTTP 503). The integration will retry on the next update."
                        )
                    if response.status >= 500:
                        raise UpdateFailed(
                            "PocketSmith is experiencing server issues (HTTP %s). "
                            "Data will refresh when the service recovers." % response.status
                        )
                    response.raise_for_status()
                    page_categories = await response.json()
                    next_url = _parse_link_next(response.headers.get("Link", ""))

            categories.extend(page_categories)
            url = next_url

        _LOGGER.debug("Fetched %s categories for user %s", len(categories), user_id)
        return categories

    async def _fetch_budget(self, session: aiohttp.ClientSession, user_id: int) -> list:
        """Return budget data for the given user."""
        url = "%s/users/%s/budget?per_page=1000" % (_API_BASE, user_id)
        budget = []

        while url:
            next_url = None

            async with asyncio.timeout(_REQUEST_TIMEOUT):
                async with session.get(url, headers=self._headers) as response:
                    if response.status == 400:
                        try:
                            error_body = (await response.json()).get("error", "unknown error")
                        except Exception:
                            error_body = "unknown error"
                        raise UpdateFailed(
                            "PocketSmith returned a bad request error: %s. This may indicate a bug in the integration." % error_body
                        )
                    if response.status == 401:
                        raise UpdateFailed(
                            "PocketSmith authentication failed — your developer key is invalid or has been revoked. "
                            "Reconfigure the integration to fix this."
                        )
                    if response.status == 403:
                        raise UpdateFailed(
                            "PocketSmith access denied — your developer key lacks the required permissions "
                            "to read your budget."
                        )
                    if response.status == 404:
                        raise UpdateFailed(
                            "PocketSmith could not find your budget data. This may be a temporary API issue."
                        )
                    if response.status == 405:
                        raise UpdateFailed(
                            "PocketSmith returned Method Not Allowed (HTTP 405). This is likely a bug in the integration — please report it."
                        )
                    if response.status == 429:
                        raise UpdateFailed(
                            "PocketSmith API rate limit exceeded. The integration will retry on the next update."
                        )
                    if response.status == 503:
                        raise UpdateFailed(
                            "PocketSmith is temporarily unavailable for maintenance (HTTP 503). The integration will retry on the next update."
                        )
                    if response.status >= 500:
                        raise UpdateFailed(
                            "PocketSmith is experiencing server issues (HTTP %s). "
                            "Data will refresh when the service recovers." % response.status
                        )
                    response.raise_for_status()
                    page_budget = await response.json()
                    next_url = _parse_link_next(response.headers.get("Link", ""))

            budget.extend(page_budget)
            url = next_url

        _LOGGER.debug("Fetched budget for user %s", user_id)
        return budget

    async def _fetch_budget_summary(self, session: aiohttp.ClientSession, user_id: int) -> list:
        """Return budget summary for the given user for the current calendar month."""
        today = date.today()
        start_date = today.replace(day=1)
        period = self._entry.options.get(CONF_PERIOD, DEFAULT_PERIOD)
        interval = self._entry.options.get(CONF_INTERVAL, DEFAULT_INTERVAL)
        url = (
            "%s/users/%s/budget_summary?period=%s&interval=%s&start_date=%s&end_date=%s&per_page=1000"
            % (_API_BASE, user_id, period, interval, start_date.isoformat(), today.isoformat())
        )

        async with asyncio.timeout(_REQUEST_TIMEOUT):
            async with session.get(url, headers=self._headers) as response:
                if response.status == 400:
                    try:
                        error_body = (await response.json()).get("error", "unknown error")
                    except Exception:
                        error_body = "unknown error"
                    raise UpdateFailed(
                        "PocketSmith returned a bad request error: %s. This may indicate a bug in the integration." % error_body
                    )
                if response.status == 401:
                    raise UpdateFailed(
                        "PocketSmith authentication failed — your developer key is invalid or has been revoked. "
                        "Reconfigure the integration to fix this."
                    )
                if response.status == 403:
                    raise UpdateFailed(
                        "PocketSmith access denied — your developer key lacks the required permissions "
                        "to read your budget summary."
                    )
                if response.status == 404:
                    raise UpdateFailed(
                        "PocketSmith could not find your budget summary data. This may be a temporary API issue."
                    )
                if response.status == 405:
                    raise UpdateFailed(
                        "PocketSmith returned Method Not Allowed (HTTP 405). This is likely a bug in the integration — please report it."
                    )
                if response.status == 429:
                    raise UpdateFailed(
                        "PocketSmith API rate limit exceeded. The integration will retry on the next update."
                    )
                if response.status == 503:
                    raise UpdateFailed(
                        "PocketSmith is temporarily unavailable for maintenance (HTTP 503). The integration will retry on the next update."
                    )
                if response.status >= 500:
                    raise UpdateFailed(
                        "PocketSmith is experiencing server issues (HTTP %s). "
                        "Data will refresh when the service recovers." % response.status
                    )
                response.raise_for_status()
                budget_summary = await response.json()

        _LOGGER.debug("Fetched budget summary for user %s", user_id)
        return budget_summary

    async def _fetch_trend_analysis(
        self,
        session: aiohttp.ClientSession,
        user_id: int,
        categories: list,
        accounts: list,
    ) -> list:
        """Return trend analysis for the given user over the past 365 days."""
        category_ids = ",".join(str(c["id"]) for c in categories)

        seen = set()
        scenario_ids_list = []
        for account in accounts:
            for scenario in account.get("scenarios", []):
                sid = scenario.get("id")
                if sid is not None and sid not in seen:
                    seen.add(sid)
                    scenario_ids_list.append(str(sid))
        scenario_ids = ",".join(scenario_ids_list)

        if not category_ids:
            _LOGGER.warning(
                "Skipping trend analysis fetch for user %s — no categories available.", user_id
            )
            return []
        if not scenario_ids:
            _LOGGER.warning(
                "Skipping trend analysis fetch for user %s — no scenarios available.", user_id
            )
            return []

        today = date.today()
        start_date = today - timedelta(days=365)
        period = "weeks"
        interval = "1"
        url = (
            "%s/users/%s/trend_analysis"
            "?period=%s&interval=%s&start_date=%s&end_date=%s&categories=%s&scenarios=%s&per_page=1000"
            % (
                _API_BASE,
                user_id,
                period,
                interval,
                start_date.isoformat(),
                today.isoformat(),
                category_ids,
                scenario_ids,
            )
        )

        trend_analysis = []
        current_url = url
        pending_422_retry = False
        alt_period = None
        alt_interval = None

        while current_url and not pending_422_retry:
            next_url = None

            async with asyncio.timeout(_REQUEST_TIMEOUT):
                async with session.get(current_url, headers=self._headers) as response:
                    if response.status == 400:
                        try:
                            error_body = (await response.json()).get("error", "unknown error")
                        except Exception:
                            error_body = "unknown error"
                        raise UpdateFailed(
                            "PocketSmith returned a bad request error: %s. This may indicate a bug in the integration." % error_body
                        )
                    if response.status == 401:
                        raise UpdateFailed(
                            "PocketSmith authentication failed — your developer key is invalid or has been revoked. "
                            "Reconfigure the integration to fix this."
                        )
                    if response.status == 403:
                        raise UpdateFailed(
                            "PocketSmith access denied — your developer key lacks the required permissions "
                            "to read your trend analysis."
                        )
                    if response.status == 404:
                        raise UpdateFailed(
                            "PocketSmith could not find your trend analysis data. This may be a temporary API issue."
                        )
                    if response.status == 405:
                        raise UpdateFailed(
                            "PocketSmith returned Method Not Allowed (HTTP 405). This is likely a bug in the integration — please report it."
                        )
                    if response.status == 422:
                        alt_period = response.headers.get("X-Suggested-Time-Period-Alternative-Type")
                        alt_interval = response.headers.get("X-Suggested-Time-Period-Alternative-Interval")
                        if alt_period and alt_interval:
                            _LOGGER.warning(
                                "PocketSmith rejected trend analysis period '%s' interval '%s' for user %s — "
                                "retrying with suggested alternative: period '%s' interval '%s'.",
                                period,
                                interval,
                                user_id,
                                alt_period,
                                alt_interval,
                            )
                            pending_422_retry = True
                        else:
                            raise UpdateFailed(
                                "PocketSmith trend analysis request was invalid — the period or date range may not be "
                                "compatible with the available budget events."
                            )
                    if response.status == 429:
                        raise UpdateFailed(
                            "PocketSmith API rate limit exceeded. The integration will retry on the next update."
                        )
                    if response.status == 503:
                        raise UpdateFailed(
                            "PocketSmith is temporarily unavailable for maintenance (HTTP 503). The integration will retry on the next update."
                        )
                    if response.status >= 500:
                        raise UpdateFailed(
                            "PocketSmith is experiencing server issues (HTTP %s). "
                            "Data will refresh when the service recovers." % response.status
                        )
                    if response.status != 422:
                        response.raise_for_status()
                        page_data = await response.json()
                        next_url = _parse_link_next(response.headers.get("Link", ""))
                        trend_analysis.extend(page_data)

            current_url = next_url

        if not pending_422_retry:
            _LOGGER.debug("Fetched trend analysis for user %s", user_id)
            return trend_analysis

        # Retry with the API-suggested period and interval.
        retry_url = (
            "%s/users/%s/trend_analysis"
            "?period=%s&interval=%s&start_date=%s&end_date=%s&categories=%s&scenarios=%s&per_page=1000"
            % (
                _API_BASE,
                user_id,
                alt_period,
                alt_interval,
                start_date.isoformat(),
                today.isoformat(),
                category_ids,
                scenario_ids,
            )
        )

        trend_analysis = []
        current_retry_url = retry_url

        while current_retry_url:
            next_retry_url = None

            async with asyncio.timeout(_REQUEST_TIMEOUT):
                async with session.get(current_retry_url, headers=self._headers) as retry_response:
                    if retry_response.status != 200:
                        raise UpdateFailed(
                            "PocketSmith trend analysis retry with period '%s' interval '%s' failed (HTTP %s)."
                            % (alt_period, alt_interval, retry_response.status)
                        )
                    page_data = await retry_response.json()
                    next_retry_url = _parse_link_next(retry_response.headers.get("Link", ""))
                    trend_analysis.extend(page_data)

            current_retry_url = next_retry_url

        _LOGGER.debug("Fetched trend analysis for user %s (via suggested alternative period)", user_id)
        return trend_analysis

    def _build_enriched_categories(self, categories: list, budget: list, trend_analysis: list) -> list:
        """Return a flat enriched list of all categories with budget and trend data."""

        def _flatten(cats, flat):
            for cat in cats:
                flat[cat["id"]] = cat
                _flatten(cat.get("children") or [], flat)

        flat_cats = {}
        _flatten(categories, flat_cats)

        budget_by_category = {}
        for pkg in budget:
            cat = pkg.get("category")
            if cat:
                budget_by_category[cat["id"]] = pkg

        trend_by_category = {}
        for pkg in trend_analysis:
            cat = pkg.get("category")
            if cat:
                trend_by_category[cat["id"]] = pkg

        result = []
        for cat_id, cat in flat_cats.items():
            parent_id = cat.get("parent_id")
            parent_title = flat_cats[parent_id]["title"] if parent_id and parent_id in flat_cats else None

            budgeted = None
            actual = None
            remaining = None
            over_by = None
            over_budget = False
            percentage_used = None
            currency = "AUD"

            pkg = budget_by_category.get(cat_id)
            if pkg:
                analysis = pkg.get("expense") or pkg.get("income")
                if analysis:
                    currency = analysis.get("currency_code", "AUD").upper()
                    current_period = next(
                        (p for p in analysis.get("periods", []) if p.get("current")),
                        None,
                    )
                    if current_period:
                        fc = current_period.get("forecast_amount")
                        ac = current_period.get("actual_amount")
                        budgeted = abs(fc) if fc is not None else None
                        actual = abs(ac) if ac is not None else None
                        remaining = current_period.get("under_by")
                        over_by = current_period.get("over_by")
                        over_budget = current_period.get("over_budget", False)
                        percentage_used = current_period.get("percentage_used")

            average_monthly = None
            average_weekly = None
            trend_pkg = trend_by_category.get(cat_id)
            if trend_pkg:
                trend_analysis_data = trend_pkg.get("expense") or trend_pkg.get("income")
                if trend_analysis_data:
                    avg = trend_analysis_data.get("average_actual_amount")
                    if avg is not None:
                        average_monthly = abs(avg)
                        average_weekly = round(average_monthly / 4.33, 2)

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
                "average_monthly": average_monthly,
                "average_weekly": average_weekly,
            })

        return result
