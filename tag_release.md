## Release Tag Checklist for home-assistant-pocketsmith
### Step 1 — Confirm your code is ready
Before tagging, make sure:
- All changes are committed and pushed to main
- You've restarted Home Assistant and verified no errors in the logs
- Sensors are reporting correctly in Developer Tools → States (search pocketsmith)

### Step 2 — Create and push the release tag

Run these two commands in Claude Code (or your terminal) from inside your repo directory:

```bash
git tag v0.4.4
git push origin tag v0.4.4
```

Let me know once that's done and I'll walk you through Step 3.