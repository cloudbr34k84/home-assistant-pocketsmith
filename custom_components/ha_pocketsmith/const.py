"""Constants for the PocketSmith integration."""
from dataclasses import dataclass, field

DOMAIN = "ha_pocketsmith"

CONF_UPDATE_INTERVAL_HOURS = "update_interval_hours"
CONF_ENABLE_BACKFILL = "enable_backfill"
CONF_ACTIVE_CURRENCY = "active_currency"

DEFAULT_UPDATE_INTERVAL_HOURS = 1
DEFAULT_ENABLE_BACKFILL = True
DEFAULT_CURRENCY = "AUD"

# Backfill status values
BACKFILL_STATUS_IDLE = "idle"
BACKFILL_STATUS_RUNNING = "running"
BACKFILL_STATUS_COMPLETE = "complete"
BACKFILL_STATUS_FAILED = "failed"


@dataclass
class BackfillState:
    """Mutable backfill progress shared between the background task and the sensor."""
    status: str = BACKFILL_STATUS_IDLE
    accounts_total: int = 0
    accounts_remaining: int = 0
    current_account: str | None = None


@dataclass
class PocketSmithData:
    """Runtime data stored on the config entry."""
    coordinator: object  # PocketSmithCoordinator — typed as object to avoid circular import
    backfill: BackfillState = field(default_factory=BackfillState)
