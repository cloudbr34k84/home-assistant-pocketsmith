[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

# PocketSmith Integration for Home Assistant

![PocketSmith Home Assistant Integration](https://raw.githubusercontent.com/cloudbr34k84/home-assistant-pocketsmith/main/brand/icon.png)

## Overview

[PocketSmith](https://www.pocketsmith.com/) is a personal finance and budgeting platform that connects to your bank accounts, tracks transactions, and projects your future cash flow. This Home Assistant integration pulls live data from the PocketSmith API and exposes it as sensors and binary sensors, giving you visibility into your account balances, budgets, and spending — right inside your smart home.

**What you get:**

- Live balance sensors for every account linked to your PocketSmith profile
- A net worth sensor summing all account balances
- Per-category spending sensors with monthly budget vs. actual tracking (pro-rated for non-bill categories, event-based for bill categories)
- Uncategorised transaction count so nothing slips through the cracks
- Binary sensors that alert you when you are over budget or have uncategorised transactions
- A user profile sensor with account metadata
- All data refreshes automatically every hour — no YAML required

---

## Prerequisites

- Home Assistant **2024.1** or later
- A PocketSmith account (any paid plan that provides API access)
- A PocketSmith **developer API key** with read permissions for accounts, transactions, categories, and budget

---

## Generating a PocketSmith Developer API Key

1. Log in to [pocketsmith.com](https://www.pocketsmith.com/) and click your profile picture in the top-right corner.
2. Select **Account Settings** from the dropdown.
3. Open the **API** tab.
4. Click **Create a new API key**.
5. Give the key a name (e.g. `Home Assistant`), add an optional description, and ensure it has **read** permissions for accounts, transactions, categories, and budget.
6. Click **Save**, then copy the key immediately — it is only shown once.
7. Store the key somewhere safe (e.g. a password manager) until you need it during setup.

> **Note:** If you lose the key, you can revoke it and generate a new one from the same API tab.

---

## Installation

### HACS (Recommended)

1. Open **HACS** in Home Assistant.
2. Go to **Integrations** and click the menu (⋮) → **Custom repositories**.
3. Add `https://github.com/cloudbr34k84/home-assistant-pocketsmith` as an **Integration**.
4. Search for **PocketSmith** in HACS and click **Download**.
5. Restart Home Assistant.

### Manual

1. Download or clone this repository.
2. Copy the `custom_components/ha_pocketsmith/` directory into your Home Assistant `config/custom_components/` folder.
3. Restart Home Assistant.

**Expected directory layout after installation:**

```
config/
└── custom_components/
    └── ha_pocketsmith/
        ├── __init__.py
        ├── binary_sensor.py
        ├── config_flow.py
        ├── const.py
        ├── coordinator.py
        ├── diagnostics.py
        ├── helpers.py
        ├── manifest.json
        ├── sensor.py
        ├── strings.json
        ├── system_health.py
        └── translations/
            └── en.json
```

---

## Configuration

1. In Home Assistant go to **Settings → Devices & Services → Add Integration**.
2. Search for **PocketSmith** and select it.
3. Enter your developer API key in the **Developer Key** field.
4. Click **Submit**. The integration validates the key against the PocketSmith API and, if successful, creates all sensors automatically.

Only one PocketSmith config entry is supported at a time. No changes to `configuration.yaml` are needed.

### Re-authentication

If your API key is revoked or replaced, remove the integration and re-add it with the new key (see [Removal](#removal) below).

---

## Sensors

All sensors belong to a single **PocketSmith** device in Home Assistant.

### Account Balance sensors

One sensor is created for each account linked to your PocketSmith user.

| Property | Value |
|---|---|
| Entity ID pattern | `sensor.pocketsmith_<account_name>_balance` |
| State | Current account balance (numeric) |
| Unit | Account currency code (e.g. `AUD`, `USD`) |
| Device class | `monetary` |
| Icon | `mdi:currency-usd` |

**Attributes:**

| Attribute | Description |
|---|---|
| `transaction_accounts` | List of sub-accounts with `id`, `account_id`, `name`, and `current_balance` |

---

### Pocketsmith Net Worth

Sums the current balance across **all** accounts.

| Property | Value |
|---|---|
| Entity ID | `sensor.pocketsmith_net_worth` |
| State | Total net worth (numeric) |
| Unit | Currency of the first account |
| Icon | `mdi:bank` |

---

### Pocketsmith Uncategorised Transactions

Counts every transaction that has no category assigned. The coordinator paginates through all your transactions to ensure an accurate total.

| Property | Value |
|---|---|
| Entity ID | `sensor.pocketsmith_uncategorised_transactions` |
| State | Number of uncategorised transactions |
| Unit | `transactions` |
| Icon | `mdi:alert-circle-outline` |

---

### Pocketsmith Categories

Reports the total number of spending/income categories (excluding transfer categories).

| Property | Value |
|---|---|
| Entity ID | `sensor.pocketsmith_categories` |
| State | Total category count |
| Icon | `mdi:cash-minus` |

**Attributes:**

| Attribute | Description |
|---|---|
| `budgeted_categories` | List of category names that have a budget set |
| `unbudgeted_categories` | List of category names with no budget |

---

### Per-category sensors

One sensor is created for each non-transfer category in your PocketSmith account, enriched with budget data scoped to the current calendar month.

| Property | Value |
|---|---|
| Entity ID pattern | `sensor.<category_name>` |
| State | Actual spend for the current calendar month (numeric, `0` if no data) |
| Unit | Category currency code |
| Icon | `mdi:cash-check` (on budget) / `mdi:cash-remove` (over budget) |

**Attributes:**

| Attribute | Description |
|---|---|
| `category_id` | PocketSmith internal category ID |
| `category_title` | Category name |
| `parent_id` | Parent category ID (if nested) |
| `parent_title` | Parent category name (if nested) |
| `is_bill` | `true` if marked as a bill in PocketSmith |
| `budgeted` | Budgeted amount for the current month. For non-bill categories this is pro-rated from the budget period to the calendar month. For bill categories this is the sum of bills scheduled this month. |
| `actual` | Actual spend from transactions this calendar month (`0` if no transactions) |
| `remaining` | Amount remaining under budget (`0` if over budget) |
| `over_by` | Amount over budget (`0` if under budget) |
| `over_budget` | `true` / `false` |
| `percentage_used` | Percentage of budget consumed (rounded to 2 decimal places) |
| `transaction_count` | Number of transactions in this category for the current month |
| `currency` | Currency code |

---

### Pocketsmith User

Reports the authenticated user's display name and exposes profile metadata as attributes.

| Property | Value |
|---|---|
| Entity ID | `sensor.pocketsmith_user` |
| State | User display name |
| Icon | `mdi:account-circle` |

**Attributes:** All fields from the PocketSmith user profile response, except `email` and `tell_a_friend_code` which are intentionally omitted.

---

## Binary Sensors

### Pocketsmith Over Budget

Turns **on** (problem) when one or more non-transfer budget categories have exceeded their monthly budget.

| Property | Value |
|---|---|
| Entity ID | `binary_sensor.pocketsmith_over_budget` |
| Device class | `problem` |
| On when | Any category's actual spend exceeds its budget |
| Icon | `mdi:alert-circle` (on) / `mdi:check-circle` (off) |

**Attributes:**

| Attribute | Description |
|---|---|
| `over_budget_count` | Number of over-budget categories |
| `categories` | List of over-budget categories, each with `category_title`, `parent_title`, `actual`, `budgeted`, `over_by`, and `percentage_used` |

---

### Pocketsmith Has Uncategorised

Turns **on** (problem) when there is at least one transaction with no category.

| Property | Value |
|---|---|
| Entity ID | `binary_sensor.pocketsmith_has_uncategorised` |
| Device class | `problem` |
| On when | `uncategorised_count > 0` |
| Icon | `mdi:tag-off` (on) / `mdi:tag-check` (off) |

**Attributes:**

| Attribute | Description |
|---|---|
| `uncategorised_count` | Number of uncategorised transactions |

---

### Pocketsmith Forecast Needs Recalculate

Turns **on** when the coordinator's last successful data fetch is older than 24 hours, or if forecast data has never been retrieved.

| Property | Value |
|---|---|
| Entity ID | `binary_sensor.pocketsmith_forecast_needs_recalculate` |
| On when | Last update timestamp is missing or older than 24 hours |
| Icon | `mdi:refresh-circle` (on) / `mdi:check-circle` (off) |

---

## Example Automations

### Alert when any account balance drops below a threshold

```yaml
alias: Low Balance Alert
trigger:
  - platform: numeric_state
    entity_id: sensor.pocketsmith_my_savings_balance
    below: 500
action:
  - service: notify.notify
    data:
      title: "Low Balance"
      message: >
        Your savings balance is {{ states('sensor.pocketsmith_my_savings_balance') }}
        {{ state_attr('sensor.pocketsmith_my_savings_balance', 'unit_of_measurement') }}.
```

### Notify when over budget

```yaml
alias: Over Budget Alert
trigger:
  - platform: state
    entity_id: binary_sensor.pocketsmith_over_budget
    to: "on"
action:
  - service: notify.notify
    data:
      title: "Budget Alert"
      message: >
        You are over budget in
        {{ state_attr('binary_sensor.pocketsmith_over_budget', 'over_budget_count') }}
        categories.
```

### Daily reminder to categorise transactions

```yaml
alias: Categorise Transactions Reminder
trigger:
  - platform: time
    at: "09:00:00"
condition:
  - condition: state
    entity_id: binary_sensor.pocketsmith_has_uncategorised
    state: "on"
action:
  - service: notify.notify
    data:
      title: "PocketSmith"
      message: >
        You have
        {{ states('sensor.pocketsmith_uncategorised_transactions') }}
        uncategorised transaction(s) to review.
```

### Weekly net worth summary

```yaml
alias: Weekly Net Worth Summary
trigger:
  - platform: time
    at: "08:00:00"
condition:
  - condition: template
    value_template: "{{ now().weekday() == 0 }}"
action:
  - service: notify.notify
    data:
      title: "Weekly Finance Summary"
      message: >
        Net worth: {{ states('sensor.pocketsmith_net_worth') }}
        {{ state_attr('sensor.pocketsmith_net_worth', 'unit_of_measurement') }}
```

### Alert when a specific category goes over budget

```yaml
alias: Groceries Over Budget
trigger:
  - platform: state
    entity_id: sensor.groceries
    attribute: over_budget
    to: true
action:
  - service: notify.notify
    data:
      title: "Budget Exceeded"
      message: >
        Groceries is over budget by
        {{ state_attr('sensor.groceries', 'over_by') }}
        {{ state_attr('sensor.groceries', 'currency') }}.
```

---

## Removal

1. Go to **Settings → Devices & Services**.
2. Find the **PocketSmith** integration card and click it.
3. Click the three-dot menu (⋮) and select **Delete**.
4. Confirm the removal.

All sensors and binary sensors created by the integration are removed automatically.

---

## Diagnostics

This integration supports the Home Assistant diagnostics feature. To download a diagnostics report:

1. Go to **Settings → Devices & Services → PocketSmith**.
2. Click the three-dot menu (⋮) and select **Download diagnostics**.

The report includes the entry configuration (with the API key redacted), current coordinator data counts (accounts, categories, budget entries), and the user profile (with email and referral code redacted). This information is useful when reporting bugs.

---

## System Health

PocketSmith reports into Home Assistant's **System Health** panel (**Settings → System → Repairs → System Health**):

| Field | Description |
|---|---|
| `api_reachable` | Whether `api.pocketsmith.com` is reachable |
| `last_activity_at` | Timestamp of the last user activity recorded by PocketSmith |
| `forecast_needs_recalculate` | Whether PocketSmith itself flags the forecast as stale |

---

## Troubleshooting

**No data / sensors unavailable**
Check **Settings → System → Logs** for errors starting with `ha_pocketsmith`. Common causes:
- Invalid or revoked API key → remove the integration and re-add it with a valid key
- API key lacks the required permissions → regenerate the key with full read permissions
- PocketSmith API is temporarily down → the integration retries automatically on the next hourly update

**Duplicate sensors after reinstall**
Old entity entries may persist. Go to **Settings → Devices & Services → Entities**, filter by `pocketsmith`, and delete any stale entries before re-adding the integration.

**Re-authentication needed**
Remove the integration via **Settings → Devices & Services** and re-add it with the new key.

---

## Contributing

Issues and pull requests are welcome at the [GitHub repository](https://github.com/cloudbr34k84/home-assistant-pocketsmith).

## License

This project is licensed under the MIT License.
