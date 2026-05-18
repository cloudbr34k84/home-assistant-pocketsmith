"""Long-term statistics for PocketSmith.

Pushes account balance, net worth, category spend, and uncategorised transaction
count into HA's recorder after each coordinator update.

Historical backfill (full transaction sweep) is handled separately by backfill.py
and runs once in the background after the first coordinator refresh.

Design decisions
----------------
* async_add_external_statistics throughout — source = DOMAIN, not an entity_id,
  so statistic IDs are decoupled from the entity registry and survive renames.
* Account balances and net worth: mean_type=ARITHMETIC. A bank balance is a
  point-in-time reading, not a meter — mean is the correct aggregate.
* Category spend: has_sum=True with last_reset at the start of each calendar
  month. sum = current-month running spend, enabling month-over-month bar charts.
* Uncategorised count: mean_type=ARITHMETIC, unit_of_measurement="transactions" (dimensionless).
"""
import logging
import re
from datetime import datetime, timezone

from homeassistant.components.recorder.models import StatisticData, StatisticMeanType
from homeassistant.components.recorder.statistics import async_add_external_statistics
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Stable statistic ID helpers — exported so backfill.py can import them
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
    raw = re.sub(r"[^\da-z]+", "_", title.lower())
    return raw.strip("_") or "unnamed"


def _month_start_utc(year: int, month: int) -> datetime:
    """Return UTC midnight on the first of the given month."""
    return datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Main entry point — called by the coordinator after every successful update
# ---------------------------------------------------------------------------

def async_insert_statistics(hass: HomeAssistant, data: dict) -> None:
    """Push current coordinator snapshot into long-term statistics."""
    now = dt_util.utcnow()
    stat_start = now.replace(minute=0, second=0, microsecond=0)

    _insert_account_statistics(hass, data, stat_start)
    _insert_net_worth_statistic(hass, data, stat_start)
    _insert_category_statistics(hass, data, stat_start)
    _insert_uncategorised_statistic(hass, data, stat_start)


# ---------------------------------------------------------------------------
# Account balances
# ---------------------------------------------------------------------------

def _insert_account_statistics(hass: HomeAssistant, data: dict, stat_start: datetime) -> None:
    for account in data.get("accounts", []):
        balance = account.get("current_balance")
        if balance is None:
            continue

        account_id = account["id"]
        title = account.get("title") or "Unnamed Account"
        currency = (account.get("currency_code") or "AUD").upper()

        async_add_external_statistics(
            hass,
            {
                "has_sum": False,
                "mean_type": StatisticMeanType.ARITHMETIC,
                "name": "%s Balance" % title,
                "source": DOMAIN,
                "statistic_id": _account_statistic_id(account_id, _slug(title)),
                "unit_of_measurement": currency,
            },
            [StatisticData(start=stat_start, mean=float(balance))],
        )
        _LOGGER.debug("Inserted balance statistic for %s: %s", title, balance)


# ---------------------------------------------------------------------------
# Net worth
# ---------------------------------------------------------------------------

def _insert_net_worth_statistic(hass: HomeAssistant, data: dict, stat_start: datetime) -> None:
    user_id = data.get("user_id")
    accounts = data.get("accounts", [])
    if not accounts or user_id is None:
        return

    net_worth = sum(acc.get("current_balance") or 0 for acc in accounts)
    currency = (accounts[0].get("currency_code") or "AUD").upper()

    async_add_external_statistics(
        hass,
        {
            "has_sum": False,
            "mean_type": StatisticMeanType.ARITHMETIC,
            "name": "Net Worth",
            "source": DOMAIN,
            "statistic_id": _net_worth_statistic_id(user_id),
            "unit_of_measurement": currency,
        },
        [StatisticData(start=stat_start, mean=round(net_worth, 2))],
    )
    _LOGGER.debug("Inserted net worth statistic: %s", net_worth)


# ---------------------------------------------------------------------------
# Category spend
# ---------------------------------------------------------------------------

def _insert_category_statistics(hass: HomeAssistant, data: dict, stat_start: datetime) -> None:
    today = dt_util.now().date()
    month_reset = _month_start_utc(today.year, today.month)

    for cat in data.get("enriched_categories", []):
        actual = cat.get("actual")
        if actual is None:
            continue

        cat_id = cat["category_id"]
        cat_title = cat.get("category_title") or "Unnamed Category"
        currency = (cat.get("currency") or "AUD").upper()
        parent_title = cat.get("parent_title")
        display_name = "%s: %s" % (parent_title, cat_title) if parent_title else cat_title
        spend = float(actual)

        async_add_external_statistics(
            hass,
            {
                "has_sum": True,
                "mean_type": StatisticMeanType.NONE,
                "name": display_name,
                "source": DOMAIN,
                "statistic_id": _category_statistic_id(cat_id, _slug(cat_title)),
                "unit_of_measurement": currency,
            },
            [StatisticData(start=stat_start, state=spend, sum=spend, last_reset=month_reset)],
        )
        _LOGGER.debug("Inserted spend statistic for %s: %s", cat_title, spend)


# ---------------------------------------------------------------------------
# Uncategorised transaction count
# ---------------------------------------------------------------------------

def _insert_uncategorised_statistic(hass: HomeAssistant, data: dict, stat_start: datetime) -> None:
    user_id = data.get("user_id")
    count = data.get("uncategorised_count")
    if user_id is None or count is None:
        return

    async_add_external_statistics(
        hass,
        {
            "has_sum": False,
            "mean_type": StatisticMeanType.ARITHMETIC,
            "name": "Uncategorised Transactions",
            "source": DOMAIN,
            "statistic_id": _uncategorised_statistic_id(user_id),
            "unit_of_measurement": "transactions",
        },
        [StatisticData(start=stat_start, mean=float(count))],
    )
    _LOGGER.debug("Inserted uncategorised count statistic: %s", count)
