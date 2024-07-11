# PocketSmith Integration for Home Assistant
![images](https://github.com/cloudbr34k84/home-assistant-pocketsmith/assets/58960644/1c0cf466-9dcf-4fcc-ad4a-6ed30da3bd95)

# Overview
This sensor integration for Home Assistant fetches account balance information from the PocketSmith API and presents it as sensors within Home Assistant.

## Features
 - Retrieves account balances from PocketSmith.
 - Supports multiple accounts linked to a single PocketSmith user.
 - Automatically updates the sensor state with the latest balance information.
 - Provides additional account details as sensor attributes.
To create a developer API key in PocketSmith, follow these steps:

### Step-by-Step Guide to Create a Developer API Key in PocketSmith

1.  **Log In to PocketSmith**:
    
    *   Open your web browser and go to the [PocketSmith website](https://www.pocketsmith.com/).
    *   Click on the "Login" button at the top right corner.
    *   Enter your username and password, then click "Login."
2.  **Navigate to Account Settings**:
    
    *   Once logged in, click on your profile picture or username at the top right corner.
    *   Select "Account Settings" from the dropdown menu.
3.  **Access the Developer API Section**:
    
    *   In the Account Settings menu, find and click on the "API" tab. This is usually listed under the "Security" or "Integrations" section.
4.  **Generate a New API Key**:
    
    *   Click on the "Create a new API key" button.
    *   A form will appear asking you to enter details for the new API key.
5.  **Fill in the API Key Details**:
    
    *   Provide a name for your API key to help you remember its purpose.
    *   Optionally, you can add a description for more context.
    *   Set the permissions for the API key according to your needs. Permissions determine what actions can be performed with the key.
6.  **Save the API Key**:
    
    *   After filling in the details, click on the "Create" or "Save" button.
    *   Your new API key will be generated and displayed on the screen.
7.  **Securely Store the API Key**:
    
    *   Copy the API key and store it securely. You will not be able to view the key again once you leave the page.
    *   It's recommended to store the key in a secure password manager.
8.  **Use the API Key**:
    
    *   You can now use this API key to authenticate your requests to the PocketSmith API. Include the key in the headers of your HTTP requests as specified in the PocketSmith API documentation.

### Important Notes

*   **Security**: Treat your API key like a password. Do not share it with anyone or expose it in public repositories or client-side code.
*   **Permissions**: Carefully choose the permissions for your API key to minimize security risks. Only grant the necessary permissions required for your application.
*   **Regenerate or Revoke**: If you suspect that your API key has been compromised, regenerate or revoke it immediately from the API section in your Account Settings.

By following these steps, PocketSmith users can easily create and manage their developer API keys to integrate and automate their financial data.
## Detailed Comments Explanation
### Setup Platform (async_setup_platform):
 Initializes the PocketSmith platform by retrieving the developer key from Home Assistant's data. Fetches the user ID using the developer key. Retrieves user accounts using the user ID. Adds PocketSmithSensor entities for each user account.
 - Fetches the user ID using the  **developer key**. 
 - Retrieves user accounts using the user ID.
 -  Adds  **PocketSmithSensor** entities for each user account.

### PocketSmithAccountSensor Class:
Represents a sensor for a PocketSmith account.
Initializes with the developer key, user ID, and account information.
**Properties**:
 - **unique_id**: Generates a unique ID for each sensor.
 - **name**: Returns the sensor's name.
 - **state**: Returns the current state of the sensor (account balance).
 - **unit_of_measurement**: Returns the unit of measurement for the sensor.
 - **device_class**: Returns the device class.
 - **extra_state_attributes**: Returns additional state attributes.

### Fetching Data (`fetch_data`):
Fetches the current balance and other details from the PocketSmith API.
**Function**:
 - fetch_data: Retrieves the current balance from the PocketSmith API.
 
### Helper Functions:
Additional utility functions to retrieve user ID and account information from the PocketSmith API.
 - **get_user_id**: Retrieves the user ID using the developer key.
 - **get_user_accounts**: Retrieves the user's accounts using the user ID.

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
  developer_key: !secret pocketsmith_api

sensor:
  - platform: pocketsmith
```
2. **Restart Home Assistant**:
Restart Home Assistant to apply the changes.

## Automation Examples
### Notify on Low Balance:
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
### Log Balances Daily:
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
### Monthly Balance Summary:
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
### Balance Change Alert:
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


