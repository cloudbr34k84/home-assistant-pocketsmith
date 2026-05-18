"""Long-term statistics for PocketSmith.

Pushes account balance, net worth, category spend, and uncategorised transaction
count into HA's recorder after each coordinator update.

Design decisions
----------------
* async_add_external_statistics is used throughout (source = DOMAIN, not an
  entity_id) so statistic IDs are decoupled from the entity registry — history
  survives entity renames.
* Statistic IDs are derived from the same stable keys used by unique_id in
  sensor.py, guaranteeing continuity.
* Account balances and net worth: mean_type=ARITHMETIC, no sum. A bank balance
  is a point-in-time state, not a meter, so mean is the correct aggregate and
  no cumulative sum makes semantic sense.
* Category spend: has_sum=True with last_reset at the start of each calendar
  month. Each hourly row carries the current-month running spend as both state
  and sum. HA resets the sum at month boundaries via last_reset, enabling
  month-over-month bar charts.
* Uncategorised count: mean_type=ARITHMETIC, unit_class=None (dimensionless).
* Backfill: on first setup (no existing rows for a statistic), historical data
  is reconstructed and inserted so graphs are populated immediately.
"""
import asyncio
import calendar
import logging
import re
from datetime import date, datetime, timedelta, timezone

import aiohttp
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import StatisticData, StatisticMeanType
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    get_last_statistics,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .api import API_BASE, parse_link_next, raise_for_api_error
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

_UNIT_CLASS_MONETARY = "monetary"
_BACKFILL_MONTHS = 3


# ---------------------------------------------------------------------------
# Stable statistic ID helpers (must match sensor.py unique_id scheme)
# ---------------------------------------------------------------------------

def _account_statistic_id(account_id: int, title_slug: str) -> str:
    return "%s:account_%s_%s_balance" % (DOMAIN, account_id, title_slug)


def _net_worth_statistic_id(user_id: int) -> str:
    return "%s:user_%s_net_worth" % (DOMAIN, user_id)


def _category_statistic_id(category_id: int, category_slug: str) -> str:
    return "%s:category_%s_%s_spend" % (DOMAIN, category_id, category_slug)


def _uncategorised_statistic_id(user_id: int) -> str:
    return "%s:user_%s_uncategorised_count" % (DOMAIN, user_id)


def _slug(title: str) -> str:
    raw = title.lower().replace(" ", "_")
    return re.sub(r"[^\w]", "", raw)


def _month_start_utc(year: int, month: int) -> datetime:
    """Return UTC midnight on the first of the given month."""
    return datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)


def _has_existing_rows(hass: HomeAssistant, statistic_id: str) -> bool:
    """Return True if the recorder already has at least one row for this id."""
    result = get_last_statistics(hass, 1, statistic_id, True, {"mean", "sum", "state"})
    return bool(result and statistic_id in result)


# ---------------------------------------------------------------------------
# Main entry point called by the coordinator after every update
# ---------------------------------------------------------------------------

async def async_insert_statistics(hass: HomeAssistant, data: dict, coordinator) -> None:
    """Push current data into long-term statistics, backfilling if needed."""
    now = dt_util.utcnow()
    stat_start = now.replace(minute=0, second=0, microsecond=0)

    await _insert_account_statistics(hass, data, stat_start, coordinator)
    await _insert_net_worth_statistic(hass, data, stat_start, coordinator)
    await _insert_category_statistics(hass, data, stat_start, coordinator)
    await _insert_uncategorised_statistic(hass, data, stat_start, coordinator)


# ---------------------------------------------------------------------------
# Account balances
# ---------------------------------------------------------------------------

async def _insert_account_statistics(
    hass: HomeAssistant, data: dict, stat_start: datetime, coordinator
) -> None:
    recorder = get_instance(hass)

    for account in data.get("accounts", []):
        balance = account.get("current_balance")
        if balance is None:
            continue

        account_id = account["id"]
        title = account.get("title", "Unnamed Account")
        title_slug = title.replace(" ", "_").lower()
        currency = (account.get("currency_code") or "AUD").upper()
        statistic_id = _account_statistic_id(account_id, title_slug)

        metadata = {
            "has_sum": False,
            "mean_type": StatisticMeanType.ARITHMETIC,
            "name": "%s Balance" % title,
            "source": DOMAIN,
            "statistic_id": statistic_id,
            "unit_class": _UNIT_CLASS_MONETARY,
            "unit_of_measurement": currency,
        }

        needs_backfill = not await recorder.async_add_executor_job(
            _has_existing_rows, hass, statistic_id
        )

        if needs_backfill:
            backfill_stats = await _backfill_account_balance(
                hass, coordinator, account_id, title_slug, float(balance), currency, stat_start
            )
            if backfill_stats:
                async_add_external_statistics(hass, metadata, backfill_stats)
                _LOGGER.debug(
                    "Backfilled %d balance rows for account %s", len(backfill_stats), title
                )

        async_add_external_statistics(
            hass,
            metadata,
            [StatisticData(start=stat_start, mean=float(balance))],
        )
        _LOGGER.debug("Inserted balance statistic for %s: %s", title, balance)


async def _backfill_account_balance(
    hass: HomeAssistant,
    coordinator,
    account_id: int,
    title_slug: str,
    current_balance: float,
    currency: str,
    current_hour: datetime,
) -> list[StatisticData]:
    """Reconstruct daily end-of-day balances over _BACKFILL_MONTHS months.

    Strategy: walk the account's transactions backwards from today.  Starting
    from the known current balance, add back each transaction amount (in
    reverse chronological order) to get the balance at earlier dates.
    """
    session = async_get_clientsession(hass)

    today = dt_util.now().date()
    cutoff = today - timedelta(days=_BACKFILL_MONTHS * 30)
    start_str = cutoff.isoformat()
    end_str = today.isoformat()

    url = "%s/accounts/%s/transactions?start_date=%s&end_date=%s&per_page=1000" % (
        API_BASE, account_id, start_str, end_str
    )

    all_transactions = []
    try:
        while url:
            async with asyncio.timeout(10):
                async with session.get(url, headers=coordinator._headers) as resp:
                    await raise_for_api_error(resp, "backfill transactions for account %s" % account_id)
                    page = await resp.json()
                    link = resp.headers.get("Link", "")
            if not page:
                break
            all_transactions.extend(page)
            url = parse_link_next(link)
    except Exception as err:
        _LOGGER.warning("Could not fetch backfill transactions for account %s: %s", account_id, err)
        return []

    # Group net transaction amounts by date (descending date = most recent first).
    daily_net: dict[date, float] = {}
    for t in all_transactions:
        raw_date = t.get("date") or t.get("transaction_date")
        if not raw_date:
            continue
        try:
            tx_date = date.fromisoformat(raw_date[:10])
        except ValueError:
            continue
        daily_net[tx_date] = daily_net.get(tx_date, 0.0) + (t.get("amount") or 0.0)

    # Walk backwards from today to reconstruct end-of-day balances.
    rows: list[StatisticData] = []
    running_balance = current_balance
    for delta in range((today - cutoff).days + 1):
        d = today - timedelta(days=delta)
        if delta > 0:
            # Undo the transactions that occurred on day d+delta (the day after d)
            next_day = d + timedelta(days=1)
            running_balance -= daily_net.get(next_day, 0.0)

        # Insert as an hourly row at UTC midnight of each day (avoid the current hour).
        row_start = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc)
        if row_start >= current_hour:
            continue
        rows.append(StatisticData(start=row_start, mean=round(running_balance, 2)))

    rows.sort(key=lambda r: r.start)
    return rows


# ---------------------------------------------------------------------------
# Net worth
# ---------------------------------------------------------------------------

async def _insert_net_worth_statistic(
    hass: HomeAssistant, data: dict, stat_start: datetime, coordinator
) -> None:
    user_id = data.get("user_id")
    accounts = data.get("accounts", [])
    if not accounts or user_id is None:
        return

    net_worth = sum(acc.get("current_balance") or 0 for acc in accounts)
    currency = (accounts[0].get("currency_code") or "AUD").upper()
    statistic_id = _net_worth_statistic_id(user_id)

    metadata = {
        "has_sum": False,
        "mean_type": StatisticMeanType.ARITHMETIC,
        "name": "Net Worth",
        "source": DOMAIN,
        "statistic_id": statistic_id,
        "unit_class": _UNIT_CLASS_MONETARY,
        "unit_of_measurement": currency,
    }

    recorder = get_instance(hass)
    needs_backfill = not await recorder.async_add_executor_job(
        _has_existing_rows, hass, statistic_id
    )

    if needs_backfill:
        backfill_stats = await _backfill_net_worth(hass, coordinator, data, net_worth, stat_start)
        if backfill_stats:
            async_add_external_statistics(hass, metadata, backfill_stats)
            _LOGGER.debug("Backfilled %d net worth rows", len(backfill_stats))

    async_add_external_statistics(
        hass,
        metadata,
        [StatisticData(start=stat_start, mean=round(net_worth, 2))],
    )
    _LOGGER.debug("Inserted net worth statistic: %s", net_worth)


async def _backfill_net_worth(
    hass: HomeAssistant,
    coordinator,
    data: dict,
    current_net_worth: float,
    current_hour: datetime,
) -> list[StatisticData]:
    """Reconstruct daily net worth by summing reconstructed per-account balances."""
    session = async_get_clientsession(hass)
    today = dt_util.now().date()
    cutoff = today - timedelta(days=_BACKFILL_MONTHS * 30)
    start_str = cutoff.isoformat()
    end_str = today.isoformat()

    # Collect per-account daily nets.
    per_account_daily: dict[int, dict[date, float]] = {}
    account_balances: dict[int, float] = {}

    for account in data.get("accounts", []):
        account_id = account["id"]
        balance = account.get("current_balance")
        if balance is None:
            continue
        account_balances[account_id] = float(balance)

        url = "%s/accounts/%s/transactions?start_date=%s&end_date=%s&per_page=1000" % (
            API_BASE, account_id, start_str, end_str
        )
        daily_net: dict[date, float] = {}
        try:
            while url:
                async with asyncio.timeout(10):
                    async with session.get(url, headers=coordinator._headers) as resp:
                        await raise_for_api_error(resp, "backfill net worth account %s" % account_id)
                        page = await resp.json()
                        link = resp.headers.get("Link", "")
                if not page:
                    break
                for t in page:
                    raw_date = t.get("date") or t.get("transaction_date")
                    if not raw_date:
                        continue
                    try:
                        tx_date = date.fromisoformat(raw_date[:10])
                    except ValueError:
                        continue
                    daily_net[tx_date] = daily_net.get(tx_date, 0.0) + (t.get("amount") or 0.0)
                url = parse_link_next(link)
        except Exception as err:
            _LOGGER.warning("Skipping account %s in net worth backfill: %s", account_id, err)
            continue
        per_account_daily[account_id] = daily_net

    rows: list[StatisticData] = []
    for delta in range((today - cutoff).days + 1):
        d = today - timedelta(days=delta)
        reconstructed_nw = 0.0
        for account_id, current_balance in account_balances.items():
            daily_net = per_account_daily.get(account_id, {})
            bal = current_balance
            for sub_delta in range(delta):
                day = today - timedelta(days=sub_delta)
                bal -= daily_net.get(day, 0.0)
            reconstructed_nw += bal

        row_start = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc)
        if row_start >= current_hour:
            continue
        rows.append(StatisticData(start=row_start, mean=round(reconstructed_nw, 2)))

    rows.sort(key=lambda r: r.start)
    return rows


# ---------------------------------------------------------------------------
# Category spend
# ---------------------------------------------------------------------------

async def _insert_category_statistics(
    hass: HomeAssistant, data: dict, stat_start: datetime, coordinator
) -> None:
    recorder = get_instance(hass)
    today = dt_util.now().date()
    month_reset = _month_start_utc(today.year, today.month)

    for cat in data.get("enriched_categories", []):
        actual = cat.get("actual")
        if actual is None:
            continue

        cat_id = cat["category_id"]
        cat_title = cat.get("category_title", "")
        currency = (cat.get("currency") or "AUD").upper()
        statistic_id = _category_statistic_id(cat_id, _slug(cat_title))

        parent_title = cat.get("parent_title")
        display_name = (
            "%s: %s" % (parent_title, cat_title) if parent_title else cat_title
        )

        metadata = {
            "has_sum": True,
            "mean_type": StatisticMeanType.NONE,
            "name": display_name,
            "source": DOMAIN,
            "statistic_id": statistic_id,
            "unit_class": _UNIT_CLASS_MONETARY,
            "unit_of_measurement": currency,
        }

        needs_backfill = not await recorder.async_add_executor_job(
            _has_existing_rows, hass, statistic_id
        )

        if needs_backfill:
            backfill_stats = await _backfill_category_spend(
                hass, coordinator, data.get("user_id"), cat_id, currency
            )
            if backfill_stats:
                async_add_external_statistics(hass, metadata, backfill_stats)
                _LOGGER.debug(
                    "Backfilled %d spend rows for category %s", len(backfill_stats), cat_title
                )

        spend = float(actual)
        async_add_external_statistics(
            hass,
            metadata,
            [StatisticData(start=stat_start, state=spend, sum=spend, last_reset=month_reset)],
        )
        _LOGGER.debug("Inserted spend statistic for %s: %s", cat_title, spend)


async def _backfill_category_spend(
    hass: HomeAssistant,
    coordinator,
    user_id: int,
    category_id: int,
    currency: str,
) -> list[StatisticData]:
    """Return one StatisticData row per past month for the category."""
    session = async_get_clientsession(hass)
    today = dt_util.now().date()
    rows: list[StatisticData] = []

    for months_back in range(1, _BACKFILL_MONTHS + 1):
        # Calculate the year/month for this iteration.
        month = today.month - months_back
        year = today.year
        while month <= 0:
            month += 12
            year -= 1

        start_date = date(year, month, 1).isoformat()
        last_day = calendar.monthrange(year, month)[1]
        end_date = date(year, month, last_day).isoformat()

        url = (
            "https://api.pocketsmith.com/v2/users/%s/transactions"
            "?category_id=%s&start_date=%s&end_date=%s&per_page=1000"
        ) % (user_id, category_id, start_date, end_date)

        total = 0.0
        try:
            while url:
                async with asyncio.timeout(10):
                    async with session.get(url, headers=coordinator._headers) as resp:
                        await raise_for_api_error(
                            resp, "backfill spend for category %s %s-%s" % (category_id, year, month)
                        )
                        page = await resp.json()
                        link = resp.headers.get("Link", "")
                if not page:
                    break
                for t in page:
                    total += abs(t.get("amount") or 0.0)
                url = parse_link_next(link)
        except Exception as err:
            _LOGGER.warning(
                "Skipping category %s backfill for %s-%02d: %s", category_id, year, month, err
            )
            continue

        month_reset = _month_start_utc(year, month)
        row_start = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
        rows.append(StatisticData(
            start=row_start,
            state=round(total, 2),
            sum=round(total, 2),
            last_reset=month_reset,
        ))

    rows.sort(key=lambda r: r.start)
    return rows


# ---------------------------------------------------------------------------
# Uncategorised transaction count
# ---------------------------------------------------------------------------

async def _insert_uncategorised_statistic(
    hass: HomeAssistant, data: dict, stat_start: datetime, coordinator
) -> None:
    user_id = data.get("user_id")
    count = data.get("uncategorised_count")
    if user_id is None or count is None:
        return

    statistic_id = _uncategorised_statistic_id(user_id)

    metadata = {
        "has_sum": False,
        "mean_type": StatisticMeanType.ARITHMETIC,
        "name": "Uncategorised Transactions",
        "source": DOMAIN,
        "statistic_id": statistic_id,
        "unit_class": None,
        "unit_of_measurement": "transactions",
    }

    async_add_external_statistics(
        hass,
        metadata,
        [StatisticData(start=stat_start, mean=float(count))],
    )
    _LOGGER.debug("Inserted uncategorised count statistic: %s", count)
