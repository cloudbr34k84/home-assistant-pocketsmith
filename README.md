# PocketSmith Integration for Home Assistant

## Overview
The PocketSmith integration allows you to display account balances from PocketSmith in Home Assistant.

## Detailed Comments Explanation:

**Setup Platform (async_setup_platform)**:
Initializes the PocketSmith platform by retrieving the developer key from Home Assistant's data.
 - Fetches the user ID using the **developer key**.
 - Retrieves user accounts using the user ID.
 - Adds **PocketSmithAccountSensor** entities for each user account.
 - Adds **PocketSmithTransactionAccountSensor** entities for each transaction account associated with the user accounts.
 - Adds **PocketSmithUncategorizedTransactionsSensor** to count the number of uncategorized transactions.
 - Adds **PocketSmithTotalTransactionsSensor** to count the total number of transactions and their respective debit and credit counts.
 - Adds **PocketSmithNetWorthSensor** to calculate and show the total net worth.

**PocketSmithAccountSensor Class**:
Represents a sensor for a PocketSmith account.
Initializes with the developer key, user ID, and account information.
**Properties**:
    - **unique_id**: Generates a unique ID for each sensor.
    - **name**: Returns the sensor's name.
    - **state**: Returns the current state of the sensor (account balance).
    - **unit_of_measurement**: Returns the unit of measurement for the sensor.
    - **device_class**: Returns the device class.
    - **extra_state_attributes**: Returns additional state attributes.

**PocketSmithTransactionAccountSensor Class**:
Represents a sensor for a PocketSmith transaction account.
Initializes with the developer key, user ID, and transaction account information.
**Properties**:
    - **unique_id**: Generates a unique ID for each sensor.
    - **name**: Returns the sensor's name.
    - **state**: Returns the current state of the sensor (transaction account balance).
    - **unit_of_measurement** Returns the unit of measurement for the sensor.
    - **device_class** Returns the device class.
    - **extra_state_attributes** Returns additional state attributes.
 
**PocketSmithUncategorizedTransactionsSensor Class**:
Represents a sensor to count uncategorized transactions.
Initializes with the developer key and user ID.
**Properties**:
  - **unique_id** Generates a unique ID for each sensor.
  - **name**: Returns the sensor's name.
  - **state** Returns the current state of the sensor (number of uncategorized transactions).
  - **extra_state_attributes** Returns additional state attributes.

**PocketSmithTotalTransactionsSensor Class**:
Represents a sensor to count total transactions and their respective debit and credit counts.
Initializes with the developer key and user ID.
**Properties**:
  - **unique_id** Generates a unique ID for each sensor.
  - **name**: Returns the sensor's name.
  - **state** Returns the current state of the sensor (total number of transactions).
  - **extra_state_attributes** Returns additional state attributes (total count of debit and credit transactions).

**PocketSmithNetWorthSensor Class**:
Represents a sensor to calculate and show the total net worth.
Initializes with the developer key and user ID.
**Properties**:
   - **unique_id** Generates a unique ID for each sensor.
   - **name**: Returns the sensor's name.
   - **state** Returns the current state of the sensor (total net worth).
   - **unit_of_measurement** Returns the unit of measurement for the sensor.
   - **device_class** Returns the device class.

**Helper Functions**:
- **get_user_id**: Retrieves the user ID using the developer key.
- **get_user_accounts**: Retrieves the user's accounts using the user ID.
- **get_transaction_accounts**: Retrieves the transaction accounts for a specific account.

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
├── init.py
├── manifest.json
├── const.py
└── sensor.py
![LPHHgmmRQz8yXE1v3khgVT](https://github.com/cloudbr34k84/home-assistant-pocketsmith/assets/58960644/ab51d2a9-2c42-4244-8dd8-708f6ee02a36)


## Configuration

1. **Update `configuration.yaml`**:
Add the following configuration to your `configuration.yaml` file:
```yaml
pocketsmith:
  developer_key: YOUR_DEVELOPER_KEY

sensor:
  - platform: pocketsmith
```
2. **Restart Home Assistant**:
Restart Home Assistant to apply the changes.

## Automation Examples
**Notify on Low Balance**:
Send a notification if an account balance falls below a certain threshold.
```
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
**Log Balances Daily**:
Log the account balances to a file or Google Sheets daily.
```
alias: Log PocketSmith Balances
trigger:
  - platform: time
    at: "00:00:00"
action:
  - service: rest_command.log_balance
    data_template:
      balance: "{{ states('sensor.pocketsmith_account_123_balance') }}"
```
**Monthly Balance Summary**:
Send a summary of your account balances at the end of each month.
```
alias: Monthly Balance Summary
trigger:
  - platform: time
    at: "00:00:00"
  - platform: template
    value_template: "{{ now().day == 1 }}"
action:
  - service: notify.notify
    data_template:
      title: "Monthly Balance Summary"
      message: >
        PocketSmith Account Balances:
        - Account 123: {{ states('sensor.pocketsmith_account_123_balance') }}
        - Account 456: {{ states('sensor.pocketsmith_account_456_balance') }}
```
**Balance Change Alert**:
Notify if there's a significant change in balance.
```
alias: Balance Change Alert
trigger:
  - platform: state
    entity_id: sensor.pocketsmith_account_123_balance
condition:
  - condition: template
    value_template: "{{ (trigger.to_state.state | float) - (trigger.from_state.state | float) > 500 }}"
action:
  - service: notify.notify
    data_template:
      title: "Balance Change Alert"
      message: "Your PocketSmith account balance has changed significantly: {{ trigger.to_state.state }}."
```



## Usage

Once configured, your PocketSmith accounts will appear as sensors in Home Assistant with the current balance and the appropriate unit of measurement.

## Troubleshooting
Duplicate Sensors: If duplicate sensors appear, ensure you have unique IDs and that the integration is not being reloaded multiple times.
No Balance Displayed: Check Home Assistant logs for errors related to fetching balance and ensure the correct API keys are used.
Contributions
Feel free to contribute to this integration by submitting issues or pull requests to the GitHub repository.

## License
This project is licensed under the MIT License.


