# PocketSmith Sensor.
from homeassistant.helpers.entity import Entity
import aiohttp
import logging
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    # Set up PocketSmith sensors.
    developer_key = hass.data[DOMAIN]["developer_key"]
    try:
        user_id = await get_user_id(developer_key)
        user_accounts = await get_user_accounts(developer_key, user_id)
        async_add_entities([PocketSmithSensor(developer_key, account) for account in user_accounts])
    except Exception as e:
        _LOGGER.error(f"Error setting up PocketSmith platform: {e}")

class PocketSmithSensor(Entity):
    # Representation of a PocketSmith Sensor.

    def __init__(self, developer_key, account):
        # Initialize the sensor.
        self._developer_key = developer_key
        self._account = account
        self._state = None
        self._attributes = {}

    @property
    def unique_id(self):
        # Return a unique ID for the sensor.
        return f"pocketsmith_{self._account['id']}"

    @property
    def name(self):
        # Return the name of the sensor.
        return f"PocketSmith Account {self._account.get('title', 'Unnamed Account')}"

    @property
    def state(self):
        # Return the state of the sensor.
        return self._state

    @property
    def unit_of_measurement(self):
        # Return the unit of measurement.
        return self._account.get('currency_code', 'USD').upper()

    @property
    def device_class(self):
        # Return the device class.
        return "monetary"

    @property
    def extra_state_attributes(self):
        # Return the state attributes.
        return self._attributes

    async def async_update(self):
        # Fetch new state data for the sensor.
        try:
            self._state = await self.fetch_data()
        except Exception as e:
            _LOGGER.error(f"Error updating PocketSmith sensor: {e}")

    async def fetch_data(self):
        # Fetch data from PocketSmith API.
        headers = {
            "Accept": "application/json",
            "Authorization": f"Key {self._developer_key}"
        }
        url = f"https://api.pocketsmith.com/v2/accounts/{self._account['id']}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    _LOGGER.debug(f"Fetched data for account {self._account['id']}: {data}")
                    balance = data.get("current_balance")
                    if balance is None:
                        _LOGGER.error(f"No 'current_balance' field in response for account {self._account['id']}: {data}")
                    # Update the state attributes with all the information from the response
                    self._attributes = data
                    return balance
                else:
                    _LOGGER.error(f"Failed to fetch data for account {self._account['id']}. Status code: {response.status}")
                    return None

async def get_user_id(developer_key):
    # Retrieve the user ID using the developer key.
    url = "https://api.pocketsmith.com/v2/me"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Key {developer_key}"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("id")
            else:
                _LOGGER.error(f"Failed to retrieve user ID. Status code: {response.status}")
                response.raise_for_status()

async def get_user_accounts(developer_key, user_id):
    # Retrieve the user's accounts using the user ID.
    url = f"https://api.pocketsmith.com/v2/users/{user_id}/accounts"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Key {developer_key}"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data
            else:
                _LOGGER.error(f"Failed to retrieve user accounts. Status code: {response.status}")
                response.raise_for_status()
