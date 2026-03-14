# PocketSmith Release Workflow

## Overview
This document outlines the steps to follow after making code changes to the PocketSmith integration.

---

## Working Directory
Always make changes in:
```
/config/home-assistant-pocketsmith/custom_components/ha_pocketsmith
```

---

## Step 1 — Make Your Changes
Make your code changes using Claude Code or your editor of choice.

---

## Step 2 — Commit with Conventional Commit Messages
Use the following format for all commit messages:
```
type: short description
```

### Commit Types
| Type | Use For | Example |
|------|---------|---------|
| `feat:` | New features | `feat: add support for multiple accounts` |
| `fix:` | Bug fixes | `fix: handle 403 response correctly` |
| `chore:` | Maintenance | `chore: update dependencies` |
| `docs:` | Documentation | `docs: update README` |
| `refactor:` | Code improvements | `refactor: simplify sensor update logic` |

### Commit Command
```bash
git add .
git commit -m "fix: your description here"
git push origin main
```

---

## Step 3 — Test in Home Assistant
Restart Home Assistant and verify:
- No errors in the logs
- Sensors are showing correct data
- Go to **Developer Tools → States** and search for `pocketsmith`

---

## Step 4 — Create a Release Tag
Once you are happy with the changes, create a new version tag:
```bash
git tag v0.X.X
git push origin v0.X.X
```

### Versioning Guide
| Change Type | Example |
|-------------|---------|
| Bug fix or small improvement | `v0.2.8` → `v0.2.9` |
| New feature | `v0.2.8` → `v0.3.0` |
| Breaking change | `v0.2.8` → `v1.0.0` |

---

## Step 5 — Automated Workflows (Happens Automatically)
Once you push a tag, GitHub Actions will automatically:
1. ✅ Create a release on GitHub with release notes generated from your commit messages
2. ✅ Update `manifest.json` with the new version number
3. ✅ Validate the integration with HACS and Hassfest

You can monitor progress in the **Actions tab** on GitHub:
```
https://github.com/cloudbr34k84/home-assistant-pocketsmith/actions
```

---

## Step 6 — Pull the Updated Manifest
After the workflows complete, pull the updated `manifest.json` back to your local repo:
```bash
git pull origin main
```

---

## Quick Reference
```bash
# 1. Commit your changes
git add .
git commit -m "fix: your description here"
git push origin main

# 2. Test in Home Assistant (restart and check sensors)

# 3. Create and push a release tag
git tag v0.X.X
git push origin v0.X.X

# 4. Wait for GitHub Actions to complete

# 5. Pull the updated manifest
git pull origin main
```