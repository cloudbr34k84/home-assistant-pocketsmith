# home-assistant-pocketsmith
The PocketSmith integration allows you to display account balances from PocketSmith in Home Assistant.
PocketSmith Integration for Home Assistant
Overview
The PocketSmith integration allows you to display account balances from PocketSmith in Home Assistant.

Prerequisites
Home Assistant instance running.
PocketSmith developer key.
Installation
Download the Integration:

Download the custom component files from the GitHub repository.
Add Custom Component:

Place the pocketsmith directory in your Home Assistant custom_components directory.
Directory Structure:

arduino
Copy code
custom_components/
└── pocketsmith/
    ├── __init__.py
    ├── manifest.json
    ├── const.py
    └── sensor.py
Configuration
Update configuration.yaml:
Add the following configuration to your configuration.yaml file:

yaml
Copy code
pocketsmith:
  developer_key: YOUR_DEVELOPER_KEY

sensor:
  - platform: pocketsmith
Replace YOUR_DEVELOPER_KEY with your actual PocketSmith developer key.

Restart Home Assistant:

Restart Home Assistant to apply the changes.
Custom Component Files
__init__.py
python
Copy code
import logging
from homeassistant.helpers import discovery
from homeassistant.core import HomeAssistant
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    if DOMAIN in config:
        developer_key = config[DOMAIN].get("developer_key")
        hass.data[DOMAIN] = {"developer_key": developer_key}
        await discovery.async_load_platform(hass, "sensor", DOMAIN, {}, config)
    return True
const.py
python
Copy code
DOMAIN = "pocketsmith"
sensor.py
python
Copy code
from homeassistant.helpers.entity import Entity
import aiohttp
import logging
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    developer_key = hass.data[DOMAIN]["developer_key"]
    user_id = await get_user_id(developer_key)
    user_accounts = await get_user_accounts(developer_key, user_id)
    async_add_entities([PocketSmithSensor(developer_key, account) for account in user_accounts])

class PocketSmithSensor(Entity):
    def __init__(self, developer_key, account):
        self._developer_key = developer_key
        self._account = account
        self._state = None

    @property
    def unique_id(self):
        return f"pocketsmith_{self._account['id']}"

    @property
    def name(self):
        return f"PocketSmith Account {self._account.get('title', 'Unnamed Account')}"

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return self._account.get('currency_code', 'USD').upper()

    @property
    def device_class(self):
        return "monetary"

    async def async_update(self):
        self._state = await self.fetch_data()

    async def fetch_data(self):
        headers = {
            "Accept": "application/json",
            "Authorization": f"Key {self._developer_key}"
        }
        url = f"https://api.pocketsmith.com/v2/accounts/{self._account['id']}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                data = await response.json()
                _LOGGER.debug(f"Fetched data for account {self._account['id']}: {data}")
                balance = data.get("current_balance")
                if balance is None:
                    _LOGGER.error(f"No 'current_balance' field in response for account {self._account['id']}: {data}")
                return balance

async def get_user_id(developer_key):
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
                response.raise_for_status()

async def get_user_accounts(developer_key, user_id):
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
                response.raise_for_status()
Usage
Once configured, your PocketSmith accounts will appear as sensors in Home Assistant with the current balance and the appropriate unit of measurement.

Troubleshooting
Duplicate Sensors: If duplicate sensors appear, ensure you have unique IDs and that the integration is not being reloaded multiple times.
No Balance Displayed: Check Home Assistant logs for errors related to fetching balance and ensure the correct API keys are used.
