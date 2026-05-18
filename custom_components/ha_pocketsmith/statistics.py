"""Long-term statistics for PocketSmith.

Pushes account balance and category spend data into HA's recorder after each
coordinator update, so history survives entity renames and appears in history
graphs indefinitely.

We use async_add_external_statistics (source = DOMAIN, not an entity_id) so the
statistic_id is decoupled from the entity registry.  The ids are derived from the
same stable keys used by unique_id in sensor.py, guaranteeing continuity.
"""
import logging
import re
from datetime import datetime

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import StatisticData, StatisticMeanType
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    get_last_statistics,
)
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Unit class string for monetary values (HA converter key)
_UNIT_CLASS_MONETARY = "monetary"


def _statistic_id_for_account(account_id: int, title_slug: str) -> str:
    return "%s:account_%s_%s_balance" % (DOMAIN, account_id, title_slug)


def _statistic_id_for_category(category_id: int, category_slug: str) -> str:
    return "%s:category_%s_%s" % (DOMAIN, category_id, category_slug)


def _slug(title: str) -> str:
    raw = title.lower().replace(" ", "_")
    return re.sub(r"[^\w]", "", raw)


async def async_insert_statistics(hass: HomeAssistant, data: dict) -> None:
    """Push current coordinator data into long-term statistics."""
    now = dt_util.utcnow()
    # Statistics buckets are hourly; floor to the current hour.
    stat_start = now.replace(minute=0, second=0, microsecond=0)

    await _insert_account_statistics(hass, data, stat_start)
    await _insert_category_statistics(hass, data, stat_start)


async def _insert_account_statistics(
    hass: HomeAssistant, data: dict, stat_start: datetime
) -> None:
    """Insert one statistic row per account for the current hour."""
    recorder = get_instance(hass)

    for account in data.get("accounts", []):
        balance = account.get("current_balance")
        if balance is None:
            continue

        account_id = account["id"]
        title = account.get("title", "Unnamed Account")
        title_slug = title.replace(" ", "_").lower()
        currency = (account.get("currency_code") or "AUD").upper()
        statistic_id = _statistic_id_for_account(account_id, title_slug)

        # Fetch the last recorded sum so we can accumulate correctly.
        last_stats = await recorder.async_add_executor_job(
            get_last_statistics, hass, 1, statistic_id, True, {"sum", "state"}
        )
        last_sum = 0.0
        if last_stats and statistic_id in last_stats:
            prev = last_stats[statistic_id][0]
            last_sum = prev.get("sum") or 0.0

        # For a balance sensor the "sum" accumulates the running balance value
        # (matches what HA does for energy-style sensors).
        new_sum = last_sum + float(balance)

        metadata = {
            "has_sum": True,
            "mean_type": StatisticMeanType.NONE,
            "name": "%s Balance" % title,
            "source": DOMAIN,
            "statistic_id": statistic_id,
            "unit_class": _UNIT_CLASS_MONETARY,
            "unit_of_measurement": currency,
        }

        statistic = StatisticData(
            start=stat_start,
            state=float(balance),
            sum=new_sum,
        )

        async_add_external_statistics(hass, metadata, [statistic])
        _LOGGER.debug(
            "Inserted balance statistic for account %s (%s): balance=%s sum=%s",
            title, statistic_id, balance, new_sum,
        )


async def _insert_category_statistics(
    hass: HomeAssistant, data: dict, stat_start: datetime
) -> None:
    """Insert one statistic row per enriched category for the current hour."""
    for cat in data.get("enriched_categories", []):
        actual = cat.get("actual")
        if actual is None:
            continue

        cat_id = cat["category_id"]
        cat_title = cat.get("category_title", "")
        currency = (cat.get("currency") or "AUD").upper()
        statistic_id = _statistic_id_for_category(cat_id, _slug(cat_title))

        parent_title = cat.get("parent_title")
        display_name = (
            "%s: %s" % (parent_title, cat_title) if parent_title else cat_title
        )

        metadata = {
            "has_sum": False,
            "mean_type": StatisticMeanType.ARITHMETIC,
            "name": display_name,
            "source": DOMAIN,
            "statistic_id": statistic_id,
            "unit_class": _UNIT_CLASS_MONETARY,
            "unit_of_measurement": currency,
        }

        statistic = StatisticData(
            start=stat_start,
            mean=float(actual),
        )

        async_add_external_statistics(hass, metadata, [statistic])
        _LOGGER.debug(
            "Inserted spend statistic for category %s (%s): actual=%s",
            cat_title, statistic_id, actual,
        )
