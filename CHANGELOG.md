# Changelog

All notable changes to the PocketSmith Home Assistant integration are documented here.

---

## [v0.5.6] - 2026-05-27

### Fixed
- Fixed uncategorised transactions repair notification to link to `https://my.pocketsmith.com/login` instead of the incorrect app.pocketsmith.com URL.

---

## [v0.5.5] - 2026-05-25

### Removed
- **Over-budget repair issue** — removed the `over_budget` repair issue. It was not actionable by users mid-month and added noise to the HA repairs panel. The `binary_sensor.pocketsmith_over_budget` entity still surfaces this data for anyone who wants to build automations on it.

---

## [v0.5.4] - 2026-05-25

### Added
- **Grandparent category attributes** — category sensors now expose `grandparent_id` and `grandparent_title`, resolving the full category hierarchy (category → parent → grandparent).
- **Category metadata attributes** — surfaced `refund_behaviour`, `roll_up`, and `colour` directly from the PocketSmith category API on each category sensor.
- **Computed budget pacing attributes** — added `days_in_month`, `days_elapsed_in_month`, `days_remaining_in_month`, `daily_budget`, `daily_actual`, and `on_track` so you can track whether spend is keeping pace with budget within the current month.

---

## [v0.5.3] - 2026-05-19

### Fixed
- Removed a stray `.github/` folder that was nested inside `custom_components/ha_pocketsmith/` and was being shipped to users via HACS. Dev tooling files (workflows, release-drafter config) now live only at the repo root where GitHub Actions expects them.
- Updated `logo.png` (128×128) and `logo@2x.png` (256×256) to be a proper 1×/2× pair from the same high-resolution source. Previously `logo@2x.png` was a copy of `icon.png`.
- Fixed `StatisticMeanType` import error in `statistics.py` that caused the integration to fail loading on some HA versions.

---

## [v0.5.2] - 2026-05-19

### Fixed
- Removed invalid `StatisticMeanType` import from `backfill.py`. This symbol does not exist in the HA recorder API and caused a crash at startup on affected versions.

---

## [v0.5.1] - 2026-05-19

### Fixed
- Increased API request timeout to reduce spurious failures on slow connections.
- Fixed hassfest validation error: placeholder `{account}` in the `backfill_failed` issue title was incorrectly wrapped in single quotes.
- Improved logging throughout the API layer to make debugging easier.

### Other
- Updated README with clearer feature descriptions, configuration options, and usage examples.

---

## [v0.5.0] - 2026-05-18

### Added
- **Historical backfill** — on first setup the integration sweeps your full PocketSmith transaction history and writes it to HA long-term statistics. This lets the Energy dashboard and history graphs show data going back years, not just from the day you installed.
- **Backfill progress sensor** — a new sensor shows the current backfill status (`idle`, `running`, `complete`) and how many accounts remain, so you can see it working in real time.
- **Currency selector** — you can now pick your preferred display currency in the integration options instead of always defaulting to your PocketSmith account currency.
- **Reconfigure flow** — update your developer API key without removing and re-adding the integration.
- **Configurable polling interval** — choose how often HA fetches data from PocketSmith (options flow).
- **Repair issues** — the integration now raises HA repair issues for actionable problems (e.g. backfill failed, over-budget categories) so they surface in the HA UI rather than just logs.
- **Button entities** — added `Trigger Backfill` and `Refresh Data` button entities for manual control.
- **pytest test suite** — unit tests for backfill logic, coordinator enrichment, and sensor entities.

---

## [v0.4.6] - 2026-05-17

### Added
- Full historical backfill implementation (paginated transaction sweep, rate-limit handling, resume on restart).
- Long-term statistics for account balances, net worth, and category spend.
- Re-authentication flow so expired or rotated API keys can be updated without reconfiguring.
- Brand assets (`icon.png`, `logo.png`, etc.) added in-tree for the HA Brands Proxy API.
- LICENSE file added (MIT, copyright Brad).

### Fixed
- Standardised currency handling across all sensors and statistics.
- Fixed invalid `unit_class` value (`monetary` is not a valid HA unit class — now uses `None`).
- Fixed `statistic_id` generation for accounts with empty title slugs.
- Fixed category sensor name format.

---

## [v0.4.5] - 2026-05-10

### Fixed
- Added `device_info` to the User sensor so it appears correctly grouped under its device in the HA UI.

---

## [v0.4.4] - 2026-05-09

### Fixed
- Handled null values and added rounding to sensor states.
- Fixed budget calculation to correctly handle multiple budget packages per category.
- Fixed monthly transaction and event data source for accurate budget figures.
- Used `dt_util.utcnow()` instead of `datetime.now(timezone.utc)` for HA best practices.

---

## [v0.4.3] - 2026-05-08

### Other
- Switched release workflow to `softprops/action-gh-release` for commit-based release notes.
- Fixed auto-version workflow to skip empty commits when manifest version is already up to date.

---

## [v0.4.2] - 2026-05-07

### Added
- Bronze quality scale compliance: `runtime_data`, `has_entity_name`, `data_description`, config flow improvements, and entity removal documentation.

---

## [v0.4.1] - 2026-05-06

### Fixed
- Corrected budget sensor period lookup and category data source.
- Fixed trend sensor crash.
- Improved device grouping and HA best-practice compliance across sensors.
- Simplified sensor set — removed budget aggregates and streamlined category reporting.

---

## [v0.3.0] - 2026-05-04

### Added
- Category sensors showing spend per category.
- Budget sensors showing actual vs budgeted spend.
- Budget summary sensor.
- Trend analysis sensor.

---

## [v0.2.x] - Earlier releases

Initial releases establishing the core integration: account balance sensors, net worth sensor, config flow, and basic PocketSmith API connectivity.
