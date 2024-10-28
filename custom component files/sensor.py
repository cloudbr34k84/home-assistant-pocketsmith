import logging
import aiohttp
import async_timeout
from homeassistant.components.sensor import SensorEntity  # Use SensorEntity for sensor-specific properties
from homeassistant.helpers.aiohttp_client import async_get_clientsession  # Use Home Assistant's session manager
from homeassistant.helpers.debounce import Debouncer  # Import Debouncer for throttling updates
from .const import DOMAIN  # Import domain constant

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up PocketSmith sensors (existing and new)."""
    developer_key = hass.data[DOMAIN]["developer_key"]
    
    try:
        # Retrieve user ID and accounts from PocketSmith
        user_id = await get_user_id(hass, developer_key)
        user_accounts = await get_user_accounts(hass, developer_key, user_id)
        
        # Create PocketSmith sensors for each account
        sensors = [PocketSmithSensor(hass, developer_key, account) for account in user_accounts]
        
        # Add a sensor for uncategorised transactions
        sensors.append(PocketsmithUncategorisedTransactions(hass, developer_key, user_id))
        
        async_add_entities(sensors)
    except Exception as e:
        _LOGGER.error(f"Error setting up PocketSmith platform: {e}")

class PocketSmithSensor(SensorEntity):
    """Representation of a PocketSmith Account Balance Sensor."""

    def __init__(self, hass, developer_key, account):
        """Initialize the sensor."""
        self._hass = hass
        self._developer_key = developer_key
        self._account = account
        self._state = None
        self._attributes = {}
        self._debouncer = None  # For managing throttling updates

    @property
    def unique_id(self):
        """Return a truly unique ID for the sensor using the account ID and title."""
        # Ensure the title is converted to a format that is unique and matches your existing entity name convention
        account_title = self._account.get('title', 'Unnamed Account').replace(" ", "_").lower()
        return f"pocketsmith_{self._account['id']}_{account_title}_balance"

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"PocketSmith Account {self._account.get('title', 'Unnamed Account')} Balance"

    @property
    def state(self):
        """Return the current balance as the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement (currency)."""
        return self._account.get('currency_code', 'USD').upper()

    @property
    def device_class(self):
        """Return the device class for this sensor."""
        return "monetary"

    @property
    def icon(self):
        """Return an icon representing the sensor."""
        return "mdi:currency-usd"

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        return self._attributes

    async def async_added_to_hass(self):
        """Initialize the debouncer when added to Home Assistant."""
        if not self._debouncer:
            self._debouncer = Debouncer(
                hass=self._hass,
                logger=_LOGGER,
                cooldown=60,  # Update no more than once every 60 seconds
                immediate=True,
                function=self.async_update_data
            )

    async def async_update(self):
        """Throttle the update call using the Debouncer."""
        if self._debouncer:
            await self._debouncer.async_call()

    async def async_update_data(self):
        """Fetch the latest data from the PocketSmith API."""
        try:
            async with async_timeout.timeout(10):  # Adding a timeout for API requests
                self._state = await self.fetch_data()
        except Exception as e:
            _LOGGER.error(f"Error updating PocketSmith sensor: {e}")

    async def fetch_data(self):
        """Fetch account balance data from PocketSmith API."""
        headers = {
            "Accept": "application/json",
            "Authorization": f"Key {self._developer_key}"
        }
        url = f"https://api.pocketsmith.com/v2/accounts/{self._account['id']}"

        session = async_get_clientsession(self._hass)
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                _LOGGER.debug(f"Fetched data for account {self._account['id']}: {data}")
                
                # Set the balance as the state
                balance = data.get("current_balance", 0.0)  # Default to 0.0 if missing

                # Extract only the necessary fields
                transaction_accounts = data.get("transaction_accounts", [])
                filtered_accounts = []
                for account in transaction_accounts:
                    filtered_account = {
                        "id": account.get("id"),
                        "account_id": account.get("account_id"),
                        "name": account.get("name"),
                        "current_balance": account.get("current_balance")
                    }
                    filtered_accounts.append(filtered_account)

                # Set only the filtered attributes
                self._attributes = {"transaction_accounts": filtered_accounts}
                
                return balance
            else:
                _LOGGER.error(f"Failed to fetch data for account {self._account['id']}. Status code: {response.status}")
                return None

class PocketsmithUncategorisedTransactions(SensorEntity):
    """Representation of a PocketSmith Sensor for counting uncategorised transactions."""
    
    def __init__(self, hass, developer_key, user_id):
        """Initialize the sensor."""
        self._hass = hass
        self._developer_key = developer_key
        self._user_id = user_id
        self._state = None
        self._debouncer = None

    @property
    def unique_id(self):
        """Return a unique ID for the sensor."""
        return f"pocketsmith_{self._user_id}_uncategorised_transactions"

    @property
    def name(self):
        """Return the name of the sensor."""
        return "Pocketsmith Uncategorised Transactions"

    @property
    def state(self):
        """Return the count of uncategorized transactions."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement (transactions count)."""
        return "transactions"

    @property
    def icon(self):
        """Return an appropriate icon for the sensor."""
        return "mdi:alert-circle-outline"

    async def async_added_to_hass(self):
        """Initialize the debouncer when added to Home Assistant."""
        if not self._debouncer:
            self._debouncer = Debouncer(
                hass=self._hass,
                logger=_LOGGER,
                cooldown=300,  # Update no more than once every 5 minutes
                immediate=True,
                function=self.async_update_data
            )

    async def async_update(self):
        """Throttle the update call using the Debouncer."""
        if self._debouncer:
            await self._debouncer.async_call()

    async def async_update_data(self):
        """Fetch uncategorised transactions count from the PocketSmith API."""
        try:
            async with async_timeout.timeout(10):  # Adding a timeout for API requests
                self._state = await self.fetch_uncategorised_transactions_count()
        except Exception as e:
            _LOGGER.error(f"Error updating Pocketsmith uncategorised transactions sensor: {e}")

    async def fetch_uncategorised_transactions_count(self):
        """Fetch transactions and count those with a null category."""
        headers = {
            "Accept": "application/json",
            "Authorization": f"Key {self._developer_key}"
        }
        url = f"https://api.pocketsmith.com/v2/users/{self._user_id}/transactions"

        session = async_get_clientsession(self._hass)
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                transactions = await response.json()
                null_category_count = sum(1 for transaction in transactions if transaction.get("category") is None)
                _LOGGER.debug(f"Number of uncategorised transactions: {null_category_count}")
                return null_category_count
            else:
                _LOGGER.error(f"Failed to fetch transactions for user {self._user_id}. Status code: {response.status}")
                return None

async def get_user_id(hass, developer_key):
    """Retrieve the user ID using the developer key."""
    url = "https://api.pocketsmith.com/v2/me"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Key {developer_key}"
    }
    
    session = async_get_clientsession(hass)
    async with async_timeout.timeout(10):  # Adding a timeout for API requests
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("id")
            else:
                _LOGGER.error(f"Failed to retrieve user ID. Status code: {response.status}")
                response.raise_for_status()

async def get_user_accounts(hass, developer_key, user_id):
    """Retrieve the user's accounts using the user ID."""
    url = f"https://api.pocketsmith.com/v2/users/{user_id}/accounts"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Key {developer_key}"
    }
    
    session = async_get_clientsession(hass)
    async with async_timeout.timeout(10):  # Adding a timeout for API requests
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data
            else:
                _LOGGER.error(f"Failed to retrieve user accounts. Status code: {response.status}")
                response.raise_for_status()
