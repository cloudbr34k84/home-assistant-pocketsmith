
---

# PocketSmith Integration for Home Assistant
![images](https://github.com/cloudbr34k84/home-assistant-pocketsmith/assets/58960644/1c0cf466-9dcf-4fcc-ad4a-6ed30da3bd95)

# Overview
This integration for Home Assistant fetches account balance information from the PocketSmith API and presents it as sensors within Home Assistant. Now includes the ability to monitor uncategorized transactions, providing a more comprehensive view of your financial data.

## Features
- **Account Balances:** Retrieves up-to-date account balances from PocketSmith and displays them as sensors in Home Assistant.
- **Multiple Accounts Support:** Supports multiple accounts linked to a single PocketSmith user.
- **Uncategorized Transactions Sensor:** Track the count of uncategorized transactions, helping you ensure all transactions are correctly categorized.
- **Automatic Updates:** Automatically updates sensor states with the latest balance and transaction information at optimized intervals.
- **Additional Attributes:** Provides detailed account and transaction information as sensor attributes, including filtered transaction details for better data management.

### New Enhancements
- **Custom Icons:** Sensors now include intuitive icons to help distinguish between balance and uncategorized transaction sensors.
- **Throttled Updates:** Uses Home Assistant’s Debouncer to manage update frequencies efficiently, reducing unnecessary API calls.

## Step-by-Step Guide to Create a Developer API Key in PocketSmith

1. **Log In to PocketSmith**:
    - Open your web browser and go to the [PocketSmith website](https://www.pocketsmith.com/).
    - Click on the "Login" button at the top right corner.
    - Enter your username and password, then click "Login."
2. **Navigate to Account Settings**:
    - Click on your profile picture or username at the top right corner.
    - Select "Account Settings" from the dropdown menu.
3. **Access the Developer API Section**:
    - Click on the "API" tab in Account Settings.
4. **Generate a New API Key**:
    - Click "Create a new API key."
    - Provide a name, description, and set permissions.
5. **Save and Secure Your API Key**:
    - Copy and store the key securely (e.g., a password manager).
    - Use this API key for authentication in the PocketSmith integration.

## Integration Details

### Setup Platform (`async_setup_platform`):
Initializes the PocketSmith platform by retrieving the developer key from Home Assistant's data and fetching user ID and account details. Now, it also creates a sensor for uncategorized transactions.

### `PocketSmithSensor` Class:
Represents a sensor for a PocketSmith account balance.

**Properties**:
- **unique_id**: Generates a unique ID using account ID and title.
- **name**: Displays the sensor's name, including "Balance" for clarity.
- **state**: Shows the current account balance.
- **unit_of_measurement**: Displays the currency code.
- **device_class**: Set to "monetary" to indicate it's a financial sensor.
- **extra_state_attributes**: Returns filtered account details for more relevant information.
- **icon**: Displays the `mdi:currency-usd` icon.

### `PocketsmithUncategorisedTransactions` Class:
Provides a new sensor for counting uncategorized transactions linked to your PocketSmith account.

**Properties**:
- **unique_id**: Unique ID for the uncategorized transactions sensor.
- **name**: Displays as "Pocketsmith Uncategorised Transactions."
- **state**: Shows the count of uncategorized transactions.
- **unit_of_measurement**: Uses "transactions."
- **icon**: Uses the `mdi:alert-circle-outline` icon for visual distinction.

### Data Fetching (`fetch_data`):
Efficiently fetches account balance and transaction details from the PocketSmith API, using Home Assistant's `async_get_clientsession` for optimal performance.

### Helper Functions:
- **get_user_id**: Retrieves the user ID using the developer key.
- **get_user_accounts**: Fetches linked accounts using the user ID.

## Prerequisites
- A running Home Assistant instance.
- A PocketSmith developer key.

## Installation

1. **Download the Integration**:
   - Download the custom component files from this repository.

2. **Add Custom Component**:
   - Place the `pocketsmith` directory in your Home Assistant `custom_components` directory.

3. **Directory Structure**:
custom_components/
└── pocketsmith/
    ├── __init__.py
    ├── manifest.json
    ├── const.py
    └── sensor.py
![LPHHgmmRQz8yXE1v3khgVT](https://github.com/cloudbr34k84/home-assistant-pocketsmith/assets/58960644/ab51d2a9-2c42-4244-8dd8-708f6ee02a36)

## Configuration

1. **Update `configuration.yaml`**:
Add the following configuration to your `configuration.yaml` file:
```yaml
pocketsmith:
  developer_key: !secret pocketsmith_api

sensor:
  - platform: pocketsmith
```
2. **Restart Home Assistant**:
Restart Home Assistant to apply the changes.

## Automation Examples

### Notify on Low Balance:
Send a notification if an account balance falls below a certain threshold.
```yaml
alias: Notify on Low Balance
trigger:
  - platform: numeric_state
    entity_id: sensor.pocketsmith_account_123_balance
    below: 100
action:
  - service: notify.notify
    data:
      title: "Low Balance Alert"
      message: "Your PocketSmith account balance is below $100."
```

### Notify on Uncategorised Transactions:
Send a notification if uncategorized transactions exceed a certain number.
```yaml
alias: Notify on Uncategorised Transactions
trigger:
  - platform: numeric_state
    entity_id: sensor.pocketsmith_uncategorised_transactions
    above: 5
action:
  - service: notify.notify
    data:
      title: "Uncategorised Transactions Alert"
      message: "You have more than 5 uncategorised transactions in PocketSmith."
```

### Log Balances Daily:
Log the account balances and uncategorized transactions count to a file or Google Sheets daily.
```yaml
alias: Log PocketSmith Balances
trigger:
  - platform: time
    at: "00:00:00"
action:
  - service: rest_command.log_balance
    data_template:
      balance: "{{ states('sensor.pocketsmith_account_123_balance') }}"
      uncategorised: "{{ states('sensor.pocketsmith_uncategorised_transactions') }}"
```

### Monthly Summary:
Send a summary of your account balances and uncategorized transactions at the end of each month.
```yaml
alias: Monthly PocketSmith Summary
trigger:
  - platform: time
    at: "00:00:00"
  - platform: template
    value_template: "{{ now().day == 1 }}"
action:
  - service: notify.notify
    data_template:
      title: "Monthly PocketSmith Summary"
      message: >
        Account Balances:
        - Account 123: {{ states('sensor.pocketsmith_account_123_balance') }}
        Uncategorized Transactions: {{ states('sensor.pocketsmith_uncategorised_transactions') }}
```

## Usage

Once configured, your PocketSmith accounts will appear as sensors in Home Assistant with the current balance, uncategorized transaction count, and appropriate icons. You can use these sensors in your automations, dashboards, and notifications.

## Troubleshooting
- **Duplicate Sensors:** Ensure unique IDs are set correctly to avoid duplicates.
- **No Balance or Transaction Data:** Check Home Assistant logs for errors related to fetching data from PocketSmith and verify the API key configuration.

## Contributions
Feel free to contribute to this integration by submitting issues or pull requests to the GitHub repository.

## License
This project is licensed under the MIT License.

---

This updated README provides clear, detailed, and easy-to-understand instructions that accurately reflect the current functionality of your PocketSmith integration.
