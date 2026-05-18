"""Shared PocketSmith API helpers used by both coordinator and statistics."""
import logging

import aiohttp
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

_LOGGER = logging.getLogger(__name__)

API_BASE = "https://api.pocketsmith.com/v2"
REQUEST_TIMEOUT = 30
_MAX_RETRY_AFTER = 300


def parse_link_next(link_header: str):
    """Extract the rel="next" URL from a Link header string, or return None."""
    for part in link_header.split(","):
        if 'rel="next"' in part:
            start = part.find("<")
            end = part.find(">")
            if start != -1 and end != -1:
                return part[start + 1:end]
    return None


async def raise_for_api_error(response: aiohttp.ClientResponse, context: str) -> None:
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
            "PocketSmith rate limit hit fetching %s — retry after %ss",
            context, retry_after,
        )
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
