# PocketSmith Integration for Home Assistant

## Overview
The PocketSmith integration allows you to display account balances from PocketSmith in Home Assistant.

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

2. **Restart Home Assistant**:
Restart Home Assistant to apply the changes.

**Usage**
Once configured, your PocketSmith accounts will appear as sensors in Home Assistant with the current balance and the appropriate unit of measurement.

**Troubleshooting**
Duplicate Sensors: If duplicate sensors appear, ensure you have unique IDs and that the integration is not being reloaded multiple times.
No Balance Displayed: Check Home Assistant logs for errors related to fetching balance and ensure the correct API keys are used.
Contributions
Feel free to contribute to this integration by submitting issues or pull requests to the GitHub repository.

**License**
This project is licensed under the MIT License.


