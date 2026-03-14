---

# PocketSmith Integration for Home Assistant
![PocketSmith Home Assistant Integration](https://raw.githubusercontent.com/cloudbr34k84/home-assistant-pocketsmith/main/brand/icon.png)

# Overview
This integration for Home Assistant fetches account balance information from the PocketSmith API and presents it as sensors within Home Assistant. Includes the ability to monitor uncategorized transactions, providing a more comprehensive view of your financial data.

## Features
- **Account Balances:** Retrieves up-to-date account balances from PocketSmith and displays them as sensors in Home Assistant.
- **Multiple Accounts Support:** Supports multiple accounts linked to a single PocketSmith user.
- **Uncategorized Transactions Sensor:** Track the count of uncategorized transactions, helping you ensure all transactions are correctly categorized.
- **Automatic Updates:** Automatically updates sensor states via a shared data coordinator, reducing unnecessary API calls.
- **Additional Attributes:** Provides detailed account and transaction information as sensor attributes.
- **UI Setup:** Configured entirely through the Home Assistant UI — no YAML required.

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
    - Use this API key during the integration setup in Home Assistant.

## Integration Details

### Coordinator (`PocketSmithCoordinator`):
Manages all data fetching in a single update cycle. Retrieves the user ID, all account balances, and the uncategorised transaction count from the PocketSmith API. All sensors read from this shared coordinator — no direct API calls are made from individual sensors.

### `PocketSmithSensor` Class:
Represents a sensor for a PocketSmith account balance.

**Properties**:
- **unique_id**: Generates a unique ID using account ID and title.
- **name**: Displays the sensor's name, including "Balance" for clarity.
- **state**: Shows the current account balance.
- **unit_of_measurement**: Displays the currency code.
- **device_class**: Set to "monetary" to indicate it's a financial sensor.
- **extra_state_attributes**: Returns filtered transaction account details.
- **icon**: Displays the `mdi:currency-usd` icon.

### `PocketsmithUncategorisedTransactions` Class:
Provides a sensor for counting uncategorised transactions linked to your PocketSmith account.

**Properties**:
- **unique_id**: Unique ID for the uncategorised transactions sensor.
- **name**: Displays as "Pocketsmith Uncategorised Transactions."
- **state**: Shows the count of uncategorised transactions.
- **unit_of_measurement**: Uses "transactions."
- **icon**: Uses the `mdi:alert-circle-outline` icon for visual distinction.

## Prerequisites
- A running Home Assistant instance.
- A PocketSmith developer key.

## Installation

### HACS (Recommended)
1. Open HACS in your Home Assistant instance.
2. Search for **PocketSmith** and install it.
3. Restart Home Assistant.

### Manual
1. Download the custom component files from this repository.
2. Place the `ha_pocketsmith` directory in your Home Assistant `custom_components` directory.
3. Restart Home Assistant.

### Directory Structure
```
custom_components/
└── ha_pocketsmith/
    ├── __init__.py
    ├── manifest.json
    ├── const.py
    ├── coordinator.py
    ├── config_flow.py
    ├── sensor.py
    ├── strings.json
    └── translations/
        └── en.json
```

## Configuration

1. In Home Assistant, go to **Settings → Integrations → Add Integration**.
2. Search for **PocketSmith**.
3. Enter your PocketSmith developer key when prompted.
4. The integration will validate your key and set up your sensors automatically.

No changes to `configuration.yaml` are required.

## Automation Examples

### Notify on Low Balance:
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

Once configured, your PocketSmith accounts will appear as sensors in Home Assistant with the current balance, uncategorised transaction count, and appropriate icons. Use these sensors in your automations, dashboards, and notifications.

## Troubleshooting
- **Duplicate Sensors:** Ensure unique IDs are set correctly to avoid duplicates.
- **No Balance or Transaction Data:** Check Home Assistant logs for errors related to fetching data from PocketSmith and verify the API key is correct.
- **Re-authentication:** If your API key changes, remove the integration and re-add it via Settings → Integrations.

## Contributions
Feel free to contribute to this integration by submitting issues or pull requests to the [GitHub repository](https://github.com/cloudbr34k84/home-assistant-pocketsmith).

## License
This project is licensed under the MIT License.

---
