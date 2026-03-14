import logging
import aiohttp
import asyncio
import async_timeout
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription  # Add SensorEntityDescription
from homeassistant.helpers.aiohttp_client import async_get_clientsession  # Use Home Assistant's session manager
from homeassistant.helpers.debounce import Debouncer  # Import Debouncer for throttling updates
from .const import DOMAIN  # Import domain constant

_LOGGER = logging.getLogger(__name__)

# Define the sensor entity description for account balance
ACCOUNT_BALANCE_DESCRIPTION = SensorEntityDescription(
    key="balance",
    name="Account Balance",
    icon="mdi:currency-usd",
    device_class="monetary",
)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up PocketSmith sensors (existing and new)."""
    developer_key = hass.data[DOMAIN]["developer_key"]
    
    try:
        # Retrieve user ID and accounts from PocketSmith
        user_id = await get_user_id(hass, developer_key)
        user_accounts = await get_user_accounts(hass, developer_key, user_id)
        
        # Create PocketSmith sensors for each account
        sensors = [PocketSmithSensor(hass, developer_key, account, ACCOUNT_BALANCE_DESCRIPTION) for account in user_accounts]
        
        # Add a sensor for uncategorised transactions
        sensors.append(PocketsmithUncategorisedTransactions(hass, developer_key, user_id))
        
        async_add_entities(sensors)
    except aiohttp.ClientError as client_err:
        _LOGGER.error(f"Network error connecting to PocketSmith API: {client_err}")
    except asyncio.TimeoutError:
        _LOGGER.error("Timeout error connecting to PocketSmith API")
    except KeyError as key_err:
        _LOGGER.error(f"Required configuration value missing: {key_err}")
    except Exception as e:
        _LOGGER.error(f"Unexpected error setting up PocketSmith platform: {e}")

class PocketSmithSensor(SensorEntity):
    """Representation of a PocketSmith Account Balance Sensor."""

    def __init__(self, hass, developer_key, account, description: SensorEntityDescription):
        """Initialize the sensor."""
        self._hass = hass
        self._developer_key = developer_key
        self._account = account
        self._state = None
        self._attributes = {}
        self._debouncer = None  # For managing throttling updates
        self.entity_description = description

    @property
    def unique_id(self):
        """Return a truly unique ID for the sensor using the account ID and title."""
        # Ensure the title is converted to a format that is unique and matches your existing entity name convention
        account_title = self._account.get('title', 'Unnamed Account').replace(" ", "_").lower()
        return f"pocketsmith_{self._account['id']}_{account_title}_balance"

    @property
    def name(self):
        """Return the name of the sensor."""
        account_title = self._account.get('title', 'Unnamed Account')
        return f"PocketSmith Account {account_title} {self.entity_description.name}"

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
        return self.entity_description.device_class

    @property
    def icon(self):
        """Return an icon representing the sensor."""
        return self.entity_description.icon

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
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout while connecting to PocketSmith API")
        except aiohttp.ClientError as client_err:
            _LOGGER.error(f"Network error connecting to PocketSmith API: {client_err}")
        except Exception as e:
            _LOGGER.error(f"Unexpected error updating PocketSmith sensor: {e}")

    async def fetch_data(self):
        """Fetch account balance data from PocketSmith API."""
        headers = {
            "Accept": "application/json",
            "Authorization": f"Key {self._developer_key}"
        }
        url = f"https://api.pocketsmith.com/v2/accounts/{self._account['id']}"

        session = async_get_clientsession(self._hass)
        try:
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
                elif response.status == 401:
                    _LOGGER.error("Authentication failed: Invalid developer key")
                    return None
                elif response.status == 404:
                    _LOGGER.error(f"Account {self._account['id']} not found")
                    return None
                else:
                    _LOGGER.error(f"Failed to fetch data for account {self._account['id']}. Status code: {response.status}")
                    return None
        except aiohttp.ClientResponseError as resp_err:
            _LOGGER.error(f"Response error for account {self._account['id']}: {resp_err}")
            return None
        except aiohttp.ContentTypeError as ct_err:
            _LOGGER.error(f"Invalid content type received for account {self._account['id']}: {ct_err}")
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
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout while connecting to PocketSmith API")
        except aiohttp.ClientError as client_err:
            _LOGGER.error(f"Network error connecting to PocketSmith API: {client_err}")
        except Exception as e:
            _LOGGER.error(f"Unexpected error updating Pocketsmith uncategorised transactions sensor: {e}")

    async def fetch_uncategorised_transactions_count(self):
        """Fetch transactions and count those with a null category."""
        headers = {
            "Accept": "application/json",
            "Authorization": f"Key {self._developer_key}"
        }
        base_url = f"https://api.pocketsmith.com/v2/users/{self._user_id}/transactions"

        session = async_get_clientsession(self._hass)
        null_category_count = 0
        page = 1

        try:
            while True:
                url = f"{base_url}?page={page}"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        transactions = await response.json()
                        if not transactions:
                            break
                        null_category_count += sum(1 for t in transactions if t.get("category") is None)
                        page += 1
                    elif response.status == 401:
                        _LOGGER.error("Authentication failed: Invalid developer key")
                        return None
                    elif response.status == 404:
                        _LOGGER.error(f"User {self._user_id} not found")
                        return None
                    else:
                        _LOGGER.error(f"Failed to fetch transactions for user {self._user_id}. Status code: {response.status}")
                        return None

            _LOGGER.debug(f"Number of uncategorised transactions: {null_category_count}")
            return null_category_count
        except aiohttp.ClientResponseError as resp_err:
            _LOGGER.error(f"Response error for user {self._user_id}: {resp_err}")
            return None
        except aiohttp.ContentTypeError as ct_err:
            _LOGGER.error(f"Invalid content type received for user {self._user_id}: {ct_err}")
            return None

async def get_user_id(hass, developer_key):
    """Retrieve the user ID using the developer key."""
    url = "https://api.pocketsmith.com/v2/me"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Key {developer_key}"
    }
    
    session = async_get_clientsession(hass)
    try:
        async with async_timeout.timeout(10):  # Adding a timeout for API requests
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    user_id = data.get("id")
                    if user_id is None:
                        _LOGGER.error("PocketSmith API returned no user ID in response")
                        raise ValueError("PocketSmith API response missing 'id' field")
                    return user_id
                elif response.status == 401:
                    _LOGGER.error("Authentication failed: Invalid developer key")
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message="Authentication failed: Invalid developer key"
                    )
                else:
                    _LOGGER.error(f"Failed to retrieve user ID. Status code: {response.status}")
                    response.raise_for_status()
    except aiohttp.ClientResponseError as resp_err:
        _LOGGER.error(f"Response error when retrieving user ID: {resp_err}")
        raise
    except aiohttp.ContentTypeError as ct_err:
        _LOGGER.error(f"Invalid content type received when retrieving user ID: {ct_err}")
        raise
    except asyncio.TimeoutError:
        _LOGGER.error("Timeout when retrieving user ID")
        raise

async def get_user_accounts(hass, developer_key, user_id):
    """Retrieve the user's accounts using the user ID."""
    url = f"https://api.pocketsmith.com/v2/users/{user_id}/accounts"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Key {developer_key}"
    }
    
    session = async_get_clientsession(hass)
    try:
        async with async_timeout.timeout(10):  # Adding a timeout for API requests
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                elif response.status == 401:
                    _LOGGER.error("Authentication failed: Invalid developer key")
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message="Authentication failed: Invalid developer key"
                    )
                elif response.status == 404:
                    _LOGGER.error(f"User {user_id} not found")
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=f"User {user_id} not found"
                    )
                else:
                    _LOGGER.error(f"Failed to retrieve user accounts. Status code: {response.status}")
                    response.raise_for_status()
    except aiohttp.ClientResponseError as resp_err:
        _LOGGER.error(f"Response error when retrieving user accounts: {resp_err}")
        raise
    except aiohttp.ContentTypeError as ct_err:
        _LOGGER.error(f"Invalid content type received when retrieving user accounts: {ct_err}")
        raise
    except asyncio.TimeoutError:
        _LOGGER.error("Timeout when retrieving user accounts")
        raise
