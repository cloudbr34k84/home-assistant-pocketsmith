[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Tests](https://github.com/cloudbr34k84/home-assistant-pocketsmith/actions/workflows/tests.yaml/badge.svg)](https://github.com/cloudbr34k84/home-assistant-pocketsmith/actions/workflows/tests.yaml)
[![Validate with hassfest](https://github.com/cloudbr34k84/home-assistant-pocketsmith/actions/workflows/hassfest.yaml/badge.svg)](https://github.com/cloudbr34k84/home-assistant-pocketsmith/actions/workflows/hassfest.yaml)
[![Validate with HACS](https://github.com/cloudbr34k84/home-assistant-pocketsmith/actions/workflows/validate.yaml/badge.svg)](https://github.com/cloudbr34k84/home-assistant-pocketsmith/actions/workflows/validate.yaml)

# PocketSmith Integration for Home Assistant

![PocketSmith Home Assistant Integration](https://raw.githubusercontent.com/cloudbr34k84/home-assistant-pocketsmith/main/custom_components/ha_pocketsmith/brand/icon.png)

## Overview

[PocketSmith](https://www.pocketsmith.com/) is a personal finance and budgeting platform that connects to your bank accounts, tracks transactions, and projects your future cash flow. This Home Assistant integration pulls live data from the PocketSmith API and exposes it as sensors, binary sensors, buttons, and controls — giving you full visibility into your finances right inside your smart home.

**What you get:**

- Live balance sensors for every account linked to your PocketSmith profile
- Net worth sensor summing all account balances, with selectable display currency
- Per-category spending sensors with monthly budget vs. actual tracking
- Rollup sensors aggregating child categories under each parent
- Uncategorised transaction count so nothing slips through the cracks
- Binary sensors that alert you when you are over budget or have uncategorised transactions
- Historical backfill that populates long-term statistics graphs from your full transaction history
- Backfill progress sensor so you can see sweep status on your dashboard
- Configurable polling interval (1–24 hours) adjustable from the dashboard
- Repair issues raised automatically for uncategorised transactions and failed backfills
- Actions (services) for manual refresh, backfill reset, and budget summary queries
- No YAML required — fully UI-configured

---

## Prerequisites

- Home Assistant **2025.1** or later
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

---

## Configuration

1. In Home Assistant go to **Settings → Devices & Services → Add Integration**.
2. Search for **PocketSmith** and select it.
3. Enter your developer API key in the **Developer Key** field.
4. Click **Submit**. The integration validates the key against the PocketSmith API and, if successful, creates all entities automatically.

Only one PocketSmith config entry is supported at a time. No changes to `configuration.yaml` are needed.

### Options

Click the three-dot menu (⋮) on the PocketSmith integration card and select **Configure** to adjust:

| Option | Default | Description |
|---|---|---|
| Polling interval (hours) | 1 | How often to fetch data from PocketSmith. Lower values use more API quota. |
| Enable historical backfill | On | Fetch your full transaction history on first setup to populate long-term statistics graphs. |

### Updating your API key

If you need to replace your developer key without losing entity history, click the three-dot menu (⋮) → **Reconfigure**. Enter the new key and submit — the integration reloads in place with no data loss.

### Re-authentication

If the integration raises an authentication error, it will prompt you to re-authenticate automatically. You can also trigger this from the three-dot menu.

---

## Entities

All entities belong to a single **PocketSmith** device in Home Assistant.

### Sensors

#### Account Balance

One sensor per account linked to your PocketSmith profile.

| Property | Value |
|---|---|
| Entity ID pattern | `sensor.pocketsmith_<account_name>_balance` |
| State | Current account balance |
| Unit | Account currency code (e.g. `AUD`, `USD`) |
| Device class | `monetary` |

**Attributes:** `transaction_accounts` — list of sub-accounts with id, name, and current balance.

---

#### Net Worth

Sums the current balance across all accounts. The display currency is controlled by the **Active Currency** select entity.

| Property | Value |
|---|---|
| Entity ID | `sensor.pocketsmith_net_worth` |
| State | Total net worth |
| Unit | Selected active currency (default: first account's currency) |
| Device class | `monetary` |

---

#### Per-Category Spend

One sensor per non-transfer category, showing actual spend vs. budget for the current calendar month.

| Property | Value |
|---|---|
| Entity ID pattern | `sensor.<category_name>` |
| State | Actual spend this calendar month |
| Unit | Category currency code |
| Icon | `mdi:cash-check` (on budget) / `mdi:cash-remove` (over budget) |

**Attributes:**

| Attribute | Description |
|---|---|
| `budgeted` | Budget for the current month. Pro-rated from the budget period for regular categories; event-based for bill categories. |
| `actual` | Actual spend from transactions this month |
| `remaining` | Amount remaining under budget |
| `over_by` | Amount over budget (0 if under) |
| `over_budget` | `true` / `false` |
| `percentage_used` | Percentage of budget consumed |
| `transaction_count` | Number of transactions this month |
| `is_bill` | Whether this is a bill category |
| `parent_id` | Parent category ID (if nested) |
| `parent_title` | Parent category name (if nested) |
| `grandparent_id` | Grandparent category ID, or `null` if there is no grandparent |
| `grandparent_title` | Grandparent category name, or `null` |
| `category_level` | Depth in the category tree (1 = top-level) |
| `refund_behaviour` | PocketSmith refund handling for this category (string or `null`) |
| `roll_up` | Whether PocketSmith rolls this category up into its parent |
| `colour` | Category colour from PocketSmith (string or `null`) |
| `days_in_month` | Number of days in the current calendar month |
| `days_elapsed_in_month` | Days elapsed so far this month (including today) |
| `days_remaining_in_month` | Days remaining in the month |
| `daily_budget` | `budgeted` ÷ `days_in_month` — the per-day budget allowance |
| `daily_actual` | `actual` ÷ `days_elapsed_in_month` — the average daily spend so far |
| `on_track` | `true` when `daily_actual` ≤ `daily_budget`; `null` if either is unavailable |

---

#### Category Rollup

One sensor per parent category, aggregating actual spend across all its children.

| Property | Value |
|---|---|
| Entity ID pattern | `sensor.rollup_<category_name>` |
| State | Total actual spend across all child categories |
| Icon | `mdi:folder-open` |

**Attributes:** `actual`, `budgeted`, `remaining`, `over_budget`, `over_by`, `percentage_used`, `children` (list of child category summaries).

---

#### Uncategorised Transactions

| Property | Value |
|---|---|
| Entity ID | `sensor.pocketsmith_uncategorised_transactions` |
| State | Count of transactions with no category |
| Unit | `transactions` |

---

#### Categories (Diagnostic)

| Property | Value |
|---|---|
| Entity ID | `sensor.pocketsmith_categories` |
| State | Total category count |

**Attributes:** `budgeted_categories`, `unbudgeted_categories`.

---

#### User (Diagnostic)

| Property | Value |
|---|---|
| Entity ID | `sensor.pocketsmith_user` |
| State | User display name |

**Attributes:** Full user profile (email and referral code are redacted).

---

#### Backfill Status (Diagnostic)

Shows the current state of the historical data sweep.

| Property | Value |
|---|---|
| Entity ID | `sensor.pocketsmith_backfill_status` |
| State | `idle` / `running` / `complete` / `failed` |

**Attributes:**

| Attribute | Description |
|---|---|
| `accounts_total` | Total number of accounts to sweep |
| `accounts_remaining` | Accounts not yet swept |
| `current_account` | Account currently being swept |

---

### Binary Sensors

#### Over Budget

| Property | Value |
|---|---|
| Entity ID | `binary_sensor.pocketsmith_over_budget` |
| Device class | `problem` |
| On when | Any category's actual spend exceeds its budget |

**Attributes:** `over_budget_count`, `categories` (list with title, actual, budgeted, over_by).

---

#### Has Uncategorised

| Property | Value |
|---|---|
| Entity ID | `binary_sensor.pocketsmith_has_uncategorised` |
| Device class | `problem` |
| On when | `uncategorised_count > 0` |

---

#### Forecast Needs Recalculate

| Property | Value |
|---|---|
| Entity ID | `binary_sensor.pocketsmith_forecast_needs_recalculate` |
| On when | Last coordinator update is missing or older than 24 hours |

---

### Buttons (Config category)

| Entity | Action |
|---|---|
| `button.pocketsmith_refresh` | Trigger an immediate data refresh |
| `button.pocketsmith_reset_backfill` | Clear backfill progress and re-sweep all accounts |

---

### Number (Config category)

| Entity | Description |
|---|---|
| `number.pocketsmith_polling_interval` | Polling interval in hours (1–24). Changes take effect immediately without a restart. |

---

### Select (Config category)

| Entity | Description |
|---|---|
| `select.pocketsmith_active_currency` | Which currency the Net Worth sensor reports in. Options are derived from your account currencies. |

---

## Actions (Services)

All actions are available under **Developer Tools → Actions** or callable from automations.

### `ha_pocketsmith.refresh`

Force an immediate data refresh without waiting for the next scheduled poll.

### `ha_pocketsmith.reset_backfill`

Clear the historical backfill progress marker. All accounts will be re-swept on the next startup. Use this if a backfill failed or you want to re-import statistics from scratch.

### `ha_pocketsmith.get_budget_summary`

Returns the current budget summary as structured data. Useful in automations.

**Response fields:**

| Field | Description |
|---|---|
| `total_categories` | Total number of budget categories |
| `over_budget_count` | Number of over-budget categories |
| `over_budget_categories` | List of over-budget categories with title, budgeted, actual, over_by, percentage_used |
| `uncategorised_count` | Number of uncategorised transactions |
| `net_worth` | Sum of all account balances |

**Example automation using the response:**

```yaml
alias: Monthly Budget Report
trigger:
  - platform: time
    at: "08:00:00"
condition:
  - condition: template
    value_template: "{{ now().day == 1 }}"
action:
  - action: ha_pocketsmith.get_budget_summary
    response_variable: summary
  - action: notify.notify
    data:
      title: "Monthly Budget Summary"
      message: >
        Net worth: {{ summary.net_worth }}.
        Over budget in {{ summary.over_budget_count }} categories.
        Uncategorised transactions: {{ summary.uncategorised_count }}.
```

---

## Historical Backfill

When **Enable historical backfill** is turned on (the default), the integration sweeps your full transaction history on first setup and writes it as long-term statistics. This populates the **Statistics** graphs in Home Assistant's Energy dashboard and history cards going back as far as your PocketSmith data allows.

**How it works:**

- One paginated API sweep per account (oldest-to-newest)
- Progress is saved after each account — a restart resumes from where it left off
- On 429 rate-limit responses the sweep waits for the `Retry-After` header (capped at 5 minutes) before retrying
- Once complete, the backfill will not re-run unless you reset it via the button or action

**Monitoring progress:**

Watch the `sensor.pocketsmith_backfill_status` entity. While running, `accounts_remaining` and `current_account` attributes show live progress.

**Resetting:**

Press `button.pocketsmith_reset_backfill` or call the `ha_pocketsmith.reset_backfill` action to clear progress and re-sweep all accounts.

---

## Repair Issues

The integration automatically raises repair issues in **Settings → System → Repairs** for:

| Issue | Trigger | Resolution |
|---|---|---|
| Uncategorised transactions | `uncategorised_count > 0` | Categorise the transactions in PocketSmith |
| Backfill failed | An account sweep exhausted all retries | Reset backfill via button or action and restart |

> **Note:** Over-budget categories no longer raise a repair issue (it was not actionable mid-month). Use `binary_sensor.pocketsmith_over_budget` to build your own automations instead — see [Example Automations](#example-automations).

---

## Example Automations

### Alert when any account balance drops below a threshold

```yaml
alias: Low Balance Alert
trigger:
  - platform: numeric_state
    entity_id: sensor.pocketsmith_savings_balance
    below: 500
action:
  - action: notify.notify
    data:
      title: "Low Balance"
      message: >
        Your savings balance is {{ states('sensor.pocketsmith_savings_balance') }}
        {{ state_attr('sensor.pocketsmith_savings_balance', 'unit_of_measurement') }}.
```

### Notify when over budget

```yaml
alias: Over Budget Alert
trigger:
  - platform: state
    entity_id: binary_sensor.pocketsmith_over_budget
    to: "on"
action:
  - action: notify.notify
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
  - action: notify.notify
    data:
      title: "PocketSmith"
      message: >
        You have {{ states('sensor.pocketsmith_uncategorised_transactions') }}
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
  - action: notify.notify
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
  - action: notify.notify
    data:
      title: "Budget Exceeded"
      message: >
        Groceries is over budget by
        {{ state_attr('sensor.groceries', 'over_by') }}
        {{ state_attr('sensor.groceries', 'currency') }}.
```

### Warn when daily spend pace is off track mid-month

```yaml
alias: Groceries Pacing Alert
trigger:
  - platform: state
    entity_id: sensor.groceries
    attribute: on_track
    to: false
action:
  - action: notify.notify
    data:
      title: "Spending Pace"
      message: >
        Groceries is spending {{ state_attr('sensor.groceries', 'daily_actual') }}/day
        against a {{ state_attr('sensor.groceries', 'daily_budget') }}/day budget
        with {{ state_attr('sensor.groceries', 'days_remaining_in_month') }} days left.
```

---

## Diagnostics

This integration supports the Home Assistant diagnostics feature. To download a diagnostics report:

1. Go to **Settings → Devices & Services → PocketSmith**.
2. Click the three-dot menu (⋮) and select **Download diagnostics**.

The report includes entry configuration (API key redacted), coordinator data counts, budget package summaries, and bill category event coverage. Useful when reporting bugs.

---

## System Health

PocketSmith reports into **Settings → System → Repairs → System Health**:

| Field | Description |
|---|---|
| `api_reachable` | Whether `api.pocketsmith.com` is reachable |
| `last_activity_at` | Timestamp of the last user activity in PocketSmith |
| `forecast_needs_recalculate` | Whether PocketSmith flags the forecast as stale |

---

## Troubleshooting

**No data / sensors unavailable**
Check **Settings → System → Logs** for errors starting with `ha_pocketsmith`. Common causes:
- Invalid or revoked API key → use three-dot menu → **Reconfigure** to update the key
- API key lacks required permissions → regenerate with full read permissions
- PocketSmith API temporarily down → the integration retries automatically on the next poll

**Backfill running slowly**
The backfill is rate-limited to be polite to the API. Accounts with thousands of transactions may take several minutes. Watch `sensor.pocketsmith_backfill_status` for progress.

**Backfill stuck on `failed`**
A repair issue will be raised. Press `button.pocketsmith_reset_backfill` and restart Home Assistant to retry.

**Duplicate sensors after reinstall**
Go to **Settings → Devices & Services → Entities**, filter by `pocketsmith`, and delete stale entries before re-adding the integration.

**Net Worth showing wrong currency**
Use the `select.pocketsmith_active_currency` entity to choose the correct currency.

---

## Removal

1. Go to **Settings → Devices & Services**.
2. Find the **PocketSmith** integration card and click it.
3. Click the three-dot menu (⋮) and select **Delete**.
4. Confirm the removal.

All entities created by the integration are removed automatically.

---

## Contributing

Issues and pull requests are welcome at the [GitHub repository](https://github.com/cloudbr34k84/home-assistant-pocketsmith).

---

## License

This project is licensed under the MIT License.
