# Local Development Setup

## How It Works

The repo uses the standard HACS layout where integration files live inside `custom_components/ha_pocketsmith/`. Home Assistant needs the integration folder directly under its own `custom_components/` directory, so a symlink bridges the two.

```
/homeassistant/
├── brads_dev/
│   └── home-assistant-pocketsmith/    ← git repo (edit files here)
│       ├── custom_components/
│       │   └── ha_pocketsmith/        ← actual integration source
│       ├── tests/
│       └── ...
└── custom_components/
    └── ha_pocketsmith -> /homeassistant/brads_dev/home-assistant-pocketsmith/custom_components/ha_pocketsmith
                                       ← symlink (HA loads from here)
```

## Where to Edit

Always edit files inside the **git repo**:

```
/homeassistant/brads_dev/home-assistant-pocketsmith/custom_components/ha_pocketsmith/
```

Changes are immediately visible to Home Assistant through the symlink — no copying needed.

## Recreating the Symlink

If the symlink is ever lost (e.g. after a container rebuild), recreate it with:

```bash
ln -s /homeassistant/brads_dev/home-assistant-pocketsmith/custom_components/ha_pocketsmith \
      /homeassistant/custom_components/ha_pocketsmith
```

## After Making Changes

| Change type | What to do |
|---|---|
| Python logic, sensors, coordinators | Settings → Developer Tools → Reload (or restart HA) |
| `manifest.json` or new files | Full HA restart required |
| `strings.json` / translations | Full HA restart required |

## Git Workflow

```bash
cd /homeassistant/brads_dev/home-assistant-pocketsmith

git pull          # get latest from GitHub
# ... make changes ...
git add .
git commit -m "your message"
git push
```
