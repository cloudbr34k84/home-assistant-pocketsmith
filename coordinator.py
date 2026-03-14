"""DataUpdateCoordinator for PocketSmith."""
import asyncio
import logging

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

_API_BASE = "https://api.pocketsmith.com/v2"
_REQUEST_TIMEOUT = 10


class PocketSmithCoordinator(DataUpdateCoordinator):
    """Fetch all PocketSmith data in a single coordinated update."""

    def __init__(self, hass: HomeAssistant, developer_key: str, update_interval) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self._developer_key = developer_key
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
        except aiohttp.ClientError as err:
            raise UpdateFailed("Network error communicating with PocketSmith API: %s" % err) from err

        return {
            "user_id": user_id,
            "accounts": accounts,
            "uncategorised_count": uncategorised_count,
        }

    async def _fetch_user_id(self, session: aiohttp.ClientSession) -> int:
        """Return the authenticated user's ID."""
        url = "%s/me" % _API_BASE

        async with asyncio.timeout(_REQUEST_TIMEOUT):
            async with session.get(url, headers=self._headers) as response:
                if response.status == 401:
                    raise UpdateFailed("Authentication failed: invalid developer key")
                response.raise_for_status()
                data = await response.json()

        user_id = data.get("id")
        if user_id is None:
            raise UpdateFailed("PocketSmith API returned a user response with no 'id' field")

        _LOGGER.debug("Fetched user ID: %s", user_id)
        return user_id

    async def _fetch_accounts(self, session: aiohttp.ClientSession, user_id: int) -> list:
        """Return all accounts for the given user."""
        url = "%s/users/%s/accounts" % (_API_BASE, user_id)

        async with asyncio.timeout(_REQUEST_TIMEOUT):
            async with session.get(url, headers=self._headers) as response:
                if response.status == 401:
                    raise UpdateFailed("Authentication failed: invalid developer key")
                if response.status == 404:
                    raise UpdateFailed("User %s not found" % user_id)
                response.raise_for_status()
                accounts = await response.json()

        _LOGGER.debug("Fetched %s accounts for user %s", len(accounts), user_id)
        return accounts

    async def _fetch_uncategorised_count(self, session: aiohttp.ClientSession, user_id: int) -> int:
        """Return the count of transactions with no category across all pages."""
        base_url = "%s/users/%s/transactions" % (_API_BASE, user_id)
        count = 0
        page = 1

        while True:
            url = "%s?uncategorised=1&page=%s" % (base_url, page)

            async with asyncio.timeout(_REQUEST_TIMEOUT):
                async with session.get(url, headers=self._headers) as response:
                    if response.status == 401:
                        raise UpdateFailed("Authentication failed: invalid developer key")
                    if response.status == 404:
                        raise UpdateFailed("User %s not found" % user_id)
                    response.raise_for_status()
                    transactions = await response.json()

            if not transactions:
                break

            count += sum(1 for t in transactions if t.get("category") is None)
            _LOGGER.debug("Page %s: %s transactions fetched", page, len(transactions))
            page += 1

        _LOGGER.debug("Total uncategorised transactions for user %s: %s", user_id, count)
        return count
