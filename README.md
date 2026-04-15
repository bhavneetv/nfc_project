# NFC Productivity Tracker (Python)

## Folder Structure

```text
nfc/
  backend/
    app/
      __init__.py
      config.py
      database.py
      generate_vapid_keys.py
      main.py
      models.py
      schemas.py
      services.py
    static/
      app.js
      select.html
      
      sw.js
    .env.example
    render.yaml
    requirements.txt
  db/
    schema.sql
  pc_listener/
    .env.example
    listener.py
    requirements.txt
  scripts/
    keep_alive.py
  PDR.md
  README.md
```

## 1) Local Setup

### A. PostgreSQL

1. Create DB named `nfc_tracker`.
2. Run schema:

```bash
psql -U postgres -d nfc_tracker -f db/schema.sql
```

### B. Backend

1. Open terminal in `backend`.
2. Create virtual env and install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill values.
4. Generate VAPID keys:

```bash
python -m app.generate_vapid_keys
```

5. Put generated keys into `.env`.
6. Start API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### C. PC Listener (Windows)

1. Open terminal in `pc_listener`.
2. Create venv and install:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env`.
4. Update:
- `API_BASE_URL=http://localhost:8000`
- `USER_ID=demo-user`
- `DEVICE_ID=windows-main`

5. Start listener:

```bash
python listener.py
```

## 2) Render Deployment

1. Push this repo to GitHub.
2. In Render, create PostgreSQL instance.
3. In Render Web Service, use `backend/render.yaml` (Blueprint deploy) or set manually:
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Root dir: `backend`

4. Add env vars:
- `DATABASE_URL` (Render PostgreSQL external URL, convert to SQLAlchemy format if needed)
- `PUBLIC_BASE_URL=https://your-api.onrender.com`
- `VAPID_PUBLIC_KEY=...`
- `VAPID_PRIVATE_KEY=...`
- `VAPID_SUBJECT=mailto:you@example.com`
- `DEFAULT_USER_ID=demo-user`

5. Run SQL schema against Render DB:

```bash
psql "<render-external-db-url>" -f db/schema.sql
```

6. Create Render Cron Job every 5 minutes:
- Command: `python keep_alive.py`
- Root dir: `scripts`
- Env: `PING_URL=https://your-api.onrender.com/health`

## 3) iPhone NFC Shortcut Setup

### Unlocked iPhone flow (popup menu)

1. Shortcuts -> New Shortcut -> Add Action `Choose from Menu`.
2. Menu options: `Study`, `Coding`, `Fun`.
3. For each option add `Get Contents of URL`:
- URL: `https://your-api.onrender.com/api/nfc/tap`
- Method: `POST`
- Request Body JSON:

Study:
```json
{"user_id":"demo-user","mode":"study","device_status":"pc_on"}
```

Coding:
```json
{"user_id":"demo-user","mode":"coding","device_status":"pc_on"}
```

Fun:
```json
{"user_id":"demo-user","mode":"fun","device_status":"pc_on"}
```

4. Automation -> NFC -> scan your NFC tag -> Run this shortcut.
5. Disable `Ask Before Running`.

### Locked iPhone flow

Program NFC tag URL as:

```text
https://your-api.onrender.com/select.html
```

When phone is locked, it opens mode selection page.

## 4) Web Push Notifications (Free)

1. Open `https://your-api.onrender.com/select.html` in Safari on iPhone.
2. Allow notifications when prompted.
3. Subscription is auto-saved via `/api/push/subscribe`.
4. Notifications sent for:
- Session stop (duration)
- 24h summary (`POST /api/notify/daily?user_id=demo-user`)
- Weekly summary (`POST /api/notify/weekly?user_id=demo-user`)
- PC off at start

### Render cron jobs for 24h and 7-day notifications

Create two cron jobs in Render:

1. Daily report (24h)
- Schedule: `0 21 * * *`
- Root dir: `scripts`
- Command: `python notify_daily.py`
- Env vars:
  - `API_BASE_URL=https://your-api.onrender.com`
  - `USER_ID=demo-user`

2. Weekly report (7 days)
- Schedule: `0 21 * * 0`
- Root dir: `scripts`
- Command: `python notify_weekly.py`
- Env vars:
  - `API_BASE_URL=https://your-api.onrender.com`
  - `USER_ID=demo-user`

3. Keep-alive ping
- Schedule: `*/4 * * * *`
- Root dir: `scripts`
- Command: `python keep_alive.py`
- Env vars:
  - `PING_URL=https://your-api.onrender.com/health`

Note: Free web services can still sleep in some cases. Keep-alive reduces sleep chances but does not guarantee 100% uptime on free plans.

## 5) API Endpoints

### Session and NFC
- `POST /api/nfc/tap`
- `POST /api/session/start`
- `POST /api/session/stop`
- `GET /api/stats?user_id=...`
- `GET /api/weekly?user_id=...`
- `GET /api/daily?user_id=...`

### Push
- `POST /api/push/subscribe`
- `POST /api/notify/daily?user_id=...`
- `POST /api/notify/weekly?user_id=...`

### Widget Data
- `GET /api/widget?user_id=...`

### PC Automation
- `POST /api/pc/heartbeat`
- `GET /api/pc/next-action?user_id=...`
- `POST /api/pc/ack`

### Health
- `GET /health`

## 6) iPhone Widget (using Scriptable or Shortcuts widget)

Use endpoint:

```text
https://your-api.onrender.com/api/widget?user_id=demo-user
```

Response includes:
- `today_total_seconds`
- `current_streak`
- `last_5_sessions`
- `pie` (`study`, `coding`, `fun` percentages)

Scriptable setup:
- Open `widget/scriptable_widget.js` and set `API_BASE` + `USER_ID`.
- In Scriptable app, create a new script and paste the file content.
- Add a Scriptable widget to home screen and select that script.
- Widget requests refresh every 2 minutes (`refreshAfterDate`) and also supports tap-to-refresh.

Notes:
- iOS may still throttle background refresh sometimes; tap-to-refresh runs immediately.
- Backend now sends `Cache-Control: no-store` on `/api/widget` to avoid stale cached data.
