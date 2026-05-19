"""Background historical backfill for PocketSmith long-term statistics.

Runs once as a fire-and-forget task spawned from async_setup_entry.
Persists progress in HA storage so it resumes correctly after a restart
rather than re-fetching everything from scratch.

Strategy
--------
One paginated transaction sweep per account (oldest-to-newest).  Each page is
fanned out simultaneously into:
  - per-day balance buckets  (for account balance + net worth statistics)
  - per-category-per-month buckets  (for category spend statistics)

This means the total number of API calls is:
    accounts × ceil(account_transaction_count / 1000)

...instead of the naive approach of:
    accounts × months  (for balances)
  + categories × months  (for category spend)

Rate limit handling
-------------------
On a 429 the sweep respects Retry-After (capped at 5 minutes), waits, then
retries the same page up to MAX_RETRIES times before skipping that account.

Resume
------
After each account is fully swept, its ID is written to HA storage.  On the
next startup the account is skipped.  If HA restarts mid-sweep (e.g., power
loss) the partially-swept account starts over from page 1 — safe because
async_add_external_statistics is idempotent for the same statistic_id + start.
"""
import asyncio
import calendar
import logging
from datetime import date, datetime, timedelta, timezone

import aiohttp
from homeassistant.components.recorder.models import StatisticData
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.components.recorder.statistics import async_add_external_statistics
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .api import API_BASE, parse_link_next, raise_for_api_error
from .const import (
    BACKFILL_STATUS_COMPLETE,
    BACKFILL_STATUS_FAILED,
    BACKFILL_STATUS_IDLE,
    BACKFILL_STATUS_RUNNING,
    CONF_ENABLE_BACKFILL,
    DEFAULT_CURRENCY,
    DEFAULT_ENABLE_BACKFILL,
    DOMAIN,
    BackfillState,
)
from .repairs import raise_backfill_failed_issue
from .statistics import (
    _account_statistic_id,
    _category_statistic_id,
    _month_start_utc,
    _net_worth_statistic_id,
    _slug,
)

_LOGGER = logging.getLogger(__name__)

_STORAGE_KEY = "%s.backfill" % DOMAIN
_STORAGE_VERSION = 1
_MAX_RETRIES = 5
_INTER_PAGE_DELAY = 0.2  # seconds between pages to be a polite API consumer


async def async_trigger_backfill(
    hass: HomeAssistant, coordinator, data: dict, entry, backfill_state: BackfillState
) -> None:
    """Spawn the backfill sweep as a background task if enabled and not already complete."""
    if not entry.options.get(CONF_ENABLE_BACKFILL, DEFAULT_ENABLE_BACKFILL):
        _LOGGER.debug("PocketSmith backfill is disabled in options — skipping")
        return

    hass.async_create_task(
        _run_backfill(hass, coordinator, data, backfill_state),
        name="pocketsmith_backfill",
        eager_start=False,
    )


async def _run_backfill(hass: HomeAssistant, coordinator, data: dict, backfill_state: BackfillState) -> None:
    """Full historical backfill — runs in the background, resumes on restart."""
    try:
        await _run_backfill_inner(hass, coordinator, data, backfill_state)
    except Exception:
        backfill_state.status = BACKFILL_STATUS_FAILED
        backfill_state.current_account = None
        _LOGGER.exception(
            "PocketSmith backfill crashed unexpectedly — progress saved so far will be "
            "retained. Restart Home Assistant to retry from the last completed account."
        )


async def _run_backfill_inner(hass: HomeAssistant, coordinator, data: dict, backfill_state: BackfillState) -> None:
    """Inner backfill implementation — called by _run_backfill inside a safety net."""
    store = Store(hass, _STORAGE_VERSION, _STORAGE_KEY)
    stored = await store.async_load() or {}
    completed_accounts: set[int] = set(stored.get("completed_accounts", []))
    all_done: bool = stored.get("all_done", False)

    if all_done:
        _LOGGER.debug("PocketSmith backfill already complete — skipping")
        backfill_state.status = BACKFILL_STATUS_COMPLETE
        backfill_state.accounts_remaining = 0
        return

    _LOGGER.info("PocketSmith backfill starting")

    accounts = data.get("accounts", [])
    user_id = data.get("user_id")
    categories = data.get("categories", [])

    # Build a flat map of category_id → category metadata for fan-out.
    cat_meta: dict[int, dict] = {}
    _flatten_categories(categories, cat_meta)

    # Track per-account current balances so we can reconstruct historical balances.
    account_current_balances: dict[int, float] = {
        acc["id"]: float(acc.get("current_balance") or 0)
        for acc in accounts
        if acc.get("current_balance") is not None
    }
    account_currencies: dict[int, str] = {
        acc["id"]: (acc.get("currency_code") or DEFAULT_CURRENCY).upper()
        for acc in accounts
    }
    account_titles: dict[int, str] = {
        acc["id"]: acc.get("title", "Unnamed Account")
        for acc in accounts
    }

    # We'll accumulate per-account daily nets and per-category-month totals.
    # After all accounts are swept we build statistics and write them in one shot.
    #
    # Structure:
    #   account_daily_nets[account_id][date] = net_amount_that_day
    #   category_month_totals[(cat_id, year, month)] = total_spend
    account_daily_nets: dict[int, dict[date, float]] = {}
    category_month_totals: dict[tuple[int, int, int], float] = {}

    session = async_get_clientsession(hass)
    today = dt_util.now().date()

    pending_accounts = [a for a in accounts if a["id"] not in completed_accounts]
    backfill_state.status = BACKFILL_STATUS_RUNNING
    backfill_state.accounts_total = len(accounts)
    backfill_state.accounts_remaining = len(pending_accounts)

    for account in accounts:
        account_id = account["id"]

        if account_id in completed_accounts:
            _LOGGER.debug("Backfill: skipping already-complete account %s", account_id)
            continue

        title = account_titles.get(account_id, str(account_id))
        backfill_state.current_account = title
        _LOGGER.info("PocketSmith backfill: sweeping account '%s' (id=%s)", title, account_id)

        daily_nets, cat_totals = await _sweep_account(
            hass, session, coordinator, account_id, cat_meta
        )

        if daily_nets is None:
            # API error exhausted retries for this account — skip it, continue with others.
            # Auth failures do not reach here; they propagate and abort the whole task.
            _LOGGER.warning(
                "Backfill: could not sweep account '%s' after retries — skipping. "
                "Statistics for this account will be incomplete until the next backfill run.",
                title,
            )
            raise_backfill_failed_issue(hass, title)
            backfill_state.accounts_remaining = max(0, backfill_state.accounts_remaining - 1)
            continue

        account_daily_nets[account_id] = daily_nets

        # Merge category totals from this account's transactions.
        for key, amount in cat_totals.items():
            category_month_totals[key] = category_month_totals.get(key, 0.0) + amount

        # Mark this account as done and persist immediately so a restart skips it.
        completed_accounts.add(account_id)
        backfill_state.accounts_remaining = max(0, backfill_state.accounts_remaining - 1)
        await store.async_save({
            "completed_accounts": list(completed_accounts),
            "all_done": False,
        })
        _LOGGER.info("PocketSmith backfill: account '%s' sweep complete", title)

    # -----------------------------------------------------------------------
    # Write account balance statistics
    # -----------------------------------------------------------------------
    _LOGGER.info("PocketSmith backfill: writing account balance statistics")
    for account_id, daily_nets in account_daily_nets.items():
        title = account_titles.get(account_id, str(account_id))
        title_slug = title.replace(" ", "_").lower()
        currency = account_currencies.get(account_id, DEFAULT_CURRENCY)
        current_balance = account_current_balances.get(account_id, 0.0)
        statistic_id = _account_statistic_id(account_id, title_slug)

        rows = _reconstruct_balance_rows(daily_nets, current_balance, today)
        if rows:
            metadata = {
                "has_sum": False,
                "name": "%s Balance" % title,
                "source": DOMAIN,
                "statistic_id": statistic_id,
                "unit_class": None,
                "unit_of_measurement": currency,
            }
            async_add_external_statistics(hass, metadata, rows)
            _LOGGER.info(
                "Backfill: inserted %d balance rows for account '%s'", len(rows), title
            )

    # -----------------------------------------------------------------------
    # Write net worth statistics (sum of all account balances per day)
    # -----------------------------------------------------------------------
    if user_id is not None and account_daily_nets:
        _LOGGER.info("PocketSmith backfill: writing net worth statistics")
        nw_rows = _reconstruct_net_worth_rows(
            account_daily_nets, account_current_balances, today
        )
        if nw_rows:
            currency = (accounts[0].get("currency_code") or DEFAULT_CURRENCY).upper() if accounts else DEFAULT_CURRENCY
            async_add_external_statistics(
                hass,
                {
                    "has_sum": False,
                    "name": "Net Worth",
                    "source": DOMAIN,
                    "statistic_id": _net_worth_statistic_id(user_id),
                    "unit_class": None,
                    "unit_of_measurement": currency,
                },
                nw_rows,
            )
            _LOGGER.info("Backfill: inserted %d net worth rows", len(nw_rows))

    # -----------------------------------------------------------------------
    # Write category spend statistics
    # -----------------------------------------------------------------------
    _LOGGER.info("PocketSmith backfill: writing category spend statistics")
    cat_rows_written = 0
    # Group by category so we can build one call per category.
    cats_seen: set[int] = set()
    for (cat_id, year, month) in category_month_totals:
        cats_seen.add(cat_id)

    for cat_id in cats_seen:
        cat_info = cat_meta.get(cat_id, {})
        cat_title = cat_info.get("title", str(cat_id))
        currency = _resolve_category_currency(cat_id, data)
        statistic_id = _category_statistic_id(cat_id, _slug(cat_title))
        parent_title = _resolve_parent_title(cat_id, cat_meta)
        display_name = "%s: %s" % (parent_title, cat_title) if parent_title else cat_title

        # Collect (start, state, last_reset) tuples sorted by date first,
        # then compute cumulative sum across months.
        unsorted_rows: list[tuple[datetime, float, datetime]] = []
        for (cid, year, month), total in category_month_totals.items():
            if cid != cat_id:
                continue
            month_reset = _month_start_utc(year, month)
            row_start = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
            unsorted_rows.append((row_start, round(total, 2), month_reset))

        unsorted_rows.sort(key=lambda r: r[0])
        month_rows: list[StatisticData] = []
        cumulative_sum = 0.0
        for row_start, state, month_reset in unsorted_rows:
            cumulative_sum += state
            month_rows.append(StatisticData(
                start=row_start,
                state=state,
                sum=round(cumulative_sum, 2),
                last_reset=month_reset,
            ))

        if month_rows:
            async_add_external_statistics(
                hass,
                {
                    "has_sum": True,
                    "name": display_name,
                    "source": DOMAIN,
                    "statistic_id": statistic_id,
                    "unit_of_measurement": currency,
                },
                month_rows,
            )
            cat_rows_written += len(month_rows)

    _LOGGER.info("Backfill: inserted %d category-month spend rows across %d categories",
                 cat_rows_written, len(cats_seen))

    # Mark fully done.
    await store.async_save({"completed_accounts": list(completed_accounts), "all_done": True})
    backfill_state.status = BACKFILL_STATUS_COMPLETE
    backfill_state.accounts_remaining = 0
    backfill_state.current_account = None
    _LOGGER.info("PocketSmith backfill complete")


# ---------------------------------------------------------------------------
# Single-account sweep
# ---------------------------------------------------------------------------

async def _sweep_account(
    hass: HomeAssistant,
    session: aiohttp.ClientSession,
    coordinator,
    account_id: int,
    cat_meta: dict[int, dict],
) -> tuple[dict[date, float] | None, dict[tuple[int, int, int], float]]:
    """Fetch ALL transactions for an account, return daily nets and category-month totals.

    Returns (None, {}) on unrecoverable error.
    """
    url = "%s/accounts/%s/transactions?per_page=1000&order=asc" % (API_BASE, account_id)
    daily_nets: dict[date, float] = {}
    cat_month_totals: dict[tuple[int, int, int], float] = {}
    page_num = 0

    while url:
        page_num += 1
        page, link, error = await _fetch_page_with_retry(
            session, coordinator, url,
            "account %s page %d" % (account_id, page_num),
        )

        if page is None:
            # Unrecoverable after retries.
            return None, {}

        for t in page:
            raw_date = t.get("date") or t.get("transaction_date")
            if not raw_date:
                continue
            try:
                tx_date = date.fromisoformat(raw_date[:10])
            except ValueError:
                continue

            amount = t.get("amount") or 0.0
            daily_nets[tx_date] = daily_nets.get(tx_date, 0.0) + float(amount)

            category = t.get("category")
            if category and not category.get("is_transfer"):
                cat_id = category.get("id")
                if cat_id is not None:
                    key = (cat_id, tx_date.year, tx_date.month)
                    cat_month_totals[key] = cat_month_totals.get(key, 0.0) + abs(float(amount))

        url = parse_link_next(link)

        if url and _INTER_PAGE_DELAY > 0:
            await asyncio.sleep(_INTER_PAGE_DELAY)

    return daily_nets, cat_month_totals


async def _fetch_page_with_retry(
    session: aiohttp.ClientSession,
    coordinator,
    url: str,
    context: str,
) -> tuple[list | None, str, bool]:
    """Fetch one page with retry on 429/5xx. Returns (data, link_header, had_error)."""
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            async with asyncio.timeout(15):
                async with session.get(url, headers=coordinator._headers) as resp:
                    if resp.status == 429:
                        retry_after_raw = resp.headers.get("Retry-After", "60")
                        try:
                            wait = min(float(retry_after_raw), 300)
                        except ValueError:
                            wait = 60.0
                        _LOGGER.warning(
                            "Backfill rate limited on %s — waiting %.0fs (attempt %d/%d)",
                            context, wait, attempt, _MAX_RETRIES,
                        )
                        await asyncio.sleep(wait)
                        continue

                    if resp.status >= 500:
                        wait = min(30 * attempt, 300)
                        _LOGGER.warning(
                            "Backfill server error %s on %s — waiting %.0fs (attempt %d/%d)",
                            resp.status, context, wait, attempt, _MAX_RETRIES,
                        )
                        await asyncio.sleep(wait)
                        continue

                    await raise_for_api_error(resp, "backfill %s" % context)
                    data = await resp.json()
                    link = resp.headers.get("Link", "")
                    return data, link, False

        except ConfigEntryAuthFailed:
            _LOGGER.error(
                "Backfill aborted on %s — PocketSmith API key is invalid or was revoked. "
                "Re-authenticate the integration and restart Home Assistant to resume.",
                context,
            )
            raise  # Propagate to _run_backfill's safety net so the whole task stops.

        except UpdateFailed as err:
            _LOGGER.error(
                "Backfill API error on %s: %s — giving up on this page after %d attempts",
                context, err, attempt,
            )
            return None, "", True

        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            wait = min(10 * attempt, 60)
            _LOGGER.warning(
                "Backfill network error on %s: %s — waiting %.0fs (attempt %d/%d)",
                context, err, wait, attempt, _MAX_RETRIES,
            )
            await asyncio.sleep(wait)

    _LOGGER.error(
        "Backfill gave up on %s after %d attempts — partial data may be missing from statistics",
        context, _MAX_RETRIES,
    )
    return None, "", True


# ---------------------------------------------------------------------------
# Balance reconstruction helpers
# ---------------------------------------------------------------------------

def _reconstruct_balance_rows(
    daily_nets: dict[date, float],
    current_balance: float,
    today: date,
) -> list[StatisticData]:
    """Walk daily_nets backwards from today to reconstruct end-of-day balances."""
    if not daily_nets:
        return []

    earliest = min(daily_nets.keys())
    rows: list[StatisticData] = []
    running = current_balance

    # Walk from today back to the earliest transaction date.
    for delta in range((today - earliest).days + 1):
        d = today - timedelta(days=delta)
        if delta > 0:
            # Undo transactions from the day after d (i.e., d+1) that moved
            # the balance forward — reversing them gives us the balance at
            # end-of-day d.
            next_day = d + timedelta(days=1)
            running -= daily_nets.get(next_day, 0.0)

        row_start = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc)
        rows.append(StatisticData(start=row_start, mean=round(running, 2)))

    rows.sort(key=lambda r: r.start)
    return rows


def _reconstruct_net_worth_rows(
    account_daily_nets: dict[int, dict[date, float]],
    account_current_balances: dict[int, float],
    today: date,
) -> list[StatisticData]:
    """Sum reconstructed per-account balances per day into net worth rows."""
    if not account_daily_nets:
        return []

    earliest = min(
        min(nets.keys())
        for nets in account_daily_nets.values()
        if nets
    )

    rows: list[StatisticData] = []
    # Per-account running balance starting from current.
    running_balances = {aid: float(bal) for aid, bal in account_current_balances.items()}

    for delta in range((today - earliest).days + 1):
        d = today - timedelta(days=delta)
        if delta > 0:
            next_day = d + timedelta(days=1)
            for account_id in running_balances:
                running_balances[account_id] -= account_daily_nets.get(account_id, {}).get(next_day, 0.0)

        nw = round(sum(running_balances.values()), 2)
        row_start = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc)
        rows.append(StatisticData(start=row_start, mean=nw))

    rows.sort(key=lambda r: r.start)
    return rows


# ---------------------------------------------------------------------------
# Category metadata helpers
# ---------------------------------------------------------------------------

def _flatten_categories(cats: list, flat: dict[int, dict]) -> None:
    for cat in cats:
        flat[cat["id"]] = cat
        _flatten_categories(cat.get("children") or [], flat)


def _resolve_parent_title(cat_id: int, cat_meta: dict[int, dict]) -> str | None:
    cat = cat_meta.get(cat_id, {})
    parent_id = cat.get("parent_id")
    if parent_id and parent_id in cat_meta:
        return cat_meta[parent_id].get("title")
    return None


def _resolve_category_currency(cat_id: int, data: dict) -> str:
    """Pull currency from enriched_categories for this cat_id, fallback AUD."""
    for ec in data.get("enriched_categories", []):
        if ec.get("category_id") == cat_id:
            return (ec.get("currency") or DEFAULT_CURRENCY).upper()
    return DEFAULT_CURRENCY
