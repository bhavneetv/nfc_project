I want to build a complete NFC-based productivity tracking system using iPhone, Node.js, PostgreSQL, and cloud hosting (Render). Generate FULL WORKING CODE (no explanations, only code + setup steps).

---

## 🎯 CORE SYSTEM BEHAVIOR

1. NFC Tap Logic:
- First tap → START session
- Second tap → STOP session
- System must detect if a session is already active

---

## 📱 MODE SELECTION

### If iPhone is UNLOCKED:
- Show popup menu:
  - Study
  - Coding
  - Fun

### If iPhone is LOCKED:
- Open a hosted web page with same options

---

## ⚙️ MODE ACTIONS

### STUDY:
- Enable Focus / DND
- Open YouTube on PC

### CODING:
- Enable Focus
- Open:
  - VS Code
  - Spotify
  - Edge browser

### FUN:
- Open:
  - YouTube
  - Netflix
  - Edge browser

---

## 💻 PC CONDITIONS

- If PC is ON:
  - Open apps automatically based on mode

- If PC is LOCKED:
  - Open browser (Edge/Chrome) with session page

- If PC is OFF:
  - Log status "PC OFF" and send info to iPhone

---

## 📊 DATA LOGGING (POSTGRESQL)

Store:

- user_id
- mode (study/coding/fun)
- start_time
- end_time
- duration
- device_status (pc_on / pc_locked / pc_off)

---

## 🔥 STREAK SYSTEM

Track:
- current_streak
- best_streak
- last_active_date

Logic:
- Increase streak if used daily
- Reset if skipped a day

---

## 📈 WEEKLY REPORT SYSTEM

Create API that returns:

- total study time
- total coding time
- total fun time
- total sessions
- last session details
- daily breakdown (7 days)

---

## 🔔 PUSH NOTIFICATIONS (100% FREE, NO APP STORE)

Requirements:

- Send notification to iPhone:
  - When session stops → show duration
  - Weekly report summary
  - If PC is OFF → notify

- Must NOT require:
  - Apple Developer paid account
  - App Store upload

Use:
- Web Push (Service Worker + VAPID or similar free method)

---

## 📊 WIDGET SYSTEM (iPhone)

Create API endpoints for widget:

- Today total time
- Current streak
- Last 5 sessions
- Pie chart data:
  - study %
  - coding %
  - fun %

---

## 🌐 FRONTEND (LOCKED PHONE PAGE)

Create simple HTML page:

- Buttons:
  - Study
  - Coding
  - Fun
- Calls backend API
- Mobile responsive

---

## 🔁 WEBHOOK / KEEP ALIVE

- Use cron or webhook system to ping server every 5 min
- Prevent Render free tier from sleeping

---

## 🖥 PC AUTOMATION

Create Node.js script that:

- Listens to backend (polling or websocket)
- Opens apps using:
  - child_process (Windows commands)

Apps:
- VS Code
- Spotify
- Edge / Chrome

---

## ☁️ HOSTING

- Backend: Render
- Database: PostgreSQL (Render DB or external)
- Must work globally (no same WiFi)

---

## 📁 REQUIRED OUTPUT

Generate:

### 1. Full Folder Structure

### 2. PostgreSQL SQL Schema

### 3. Backend Code (Node.js + Express)
- /start
- /stop
- /stats
- /weekly
- push notification logic
- streak logic
- device status handling

### 4. Frontend Code
- select.html

### 5. Service Worker + Web Push Setup

### 6. PC Listener Script

### 7. Setup Instructions:
- How to run locally
- How to deploy on Render
- How to connect PostgreSQL

### 8. iPhone Shortcut Steps:
- NFC trigger
- API calls
- menu handling

---

## ⚠️ IMPORTANT RULES

- Code must be COMPLETE (no missing parts)
- Beginner-friendly
- No paid services
- No App Store dependency
- Everything must work together
- Clean folder structure