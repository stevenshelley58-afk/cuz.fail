# Uptime Monitoring — DraftCheck V3

## Monitor targets

| URL | Purpose | Expected response |
|-----|---------|-------------------|
| `https://lotfile.app/api/v1/health` | Primary health probe (DB ping) | HTTP 200, `{"status":"ok","db":"ok"}` |
| `https://lotfile.app/api/v1/ready` | Deep-ready probe (DB + queue + storage) | HTTP 200, `{"status":"ok"}` |

Both endpoints are unauthenticated.
A `"status":"degraded"` response still returns HTTP 200 — configure the monitor to
check body content for `"status":"ok"` rather than relying on status code alone.

## UptimeRobot setup (free tier)

1. Sign in at <https://uptimerobot.com>
2. **Add New Monitor**
   - Type: HTTPS
   - Friendly Name: `LotFile health`
   - URL: `https://lotfile.app/api/v1/health`
   - Monitoring Interval: 5 minutes
   - Alert Contact: `stevenshelley58@gmail.com`
   - Keyword: `"status":"ok"` (Alert if keyword not found)
3. Repeat for `/api/v1/ready` as a secondary monitor.

## Re-registration

If the UptimeRobot account needs to be recreated (key rotation, credential loss):
1. Follow the steps above.
2. Update this doc with the new monitor IDs.

## Alert thresholds

- **Down alert**: after 2 consecutive failures (10 min)
- **Recovery alert**: on first success after a down event
