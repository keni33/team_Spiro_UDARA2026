# StructGuard AI — Setup & Run Guide
**Team Spiro | UDARA Bootcamp 2025**

---

## What You're Running

```
Your Computer
├── Backend (Flask/Python) → runs at http://localhost:5000
│     Handles: login, database, AI analysis, PDF reports
│
└── Frontend (HTML/CSS/JS) → open in browser
      Handles: all screens, forms, dashboard UI
```

The frontend talks to the backend through API calls.
You need **both running at the same time**.

---

## Prerequisites (One-time Setup)

### 1. Check Python is installed
Open your terminal and run:
```bash
python --version
# Should show Python 3.10 or higher
```
If not installed: https://www.python.org/downloads/

### 2. Check pip is installed
```bash
pip --version
```

### 3. Install a code editor (if you don't have one)
Recommended: **VS Code** → https://code.visualstudio.com
Install the **Live Server** extension inside VS Code (search "Live Server" by Ritwick Dey).

---

## First-Time Setup (Run These Once)

Open a terminal in the `structguard/` folder, then:

### Step 1 — Copy the environment config
```bash
cp .env.example .env
```
Open `.env` and check the values. For local development, the defaults work fine.

### Step 2 — Install Python packages
```bash
pip install -r backend/requirements.txt
```
This installs Flask, SQLAlchemy, JWT, Anthropic, ReportLab, etc.

> ⚠️ If pip gives errors, try: `pip install -r backend/requirements.txt --break-system-packages`
> Or use a virtual environment (see Advanced section at bottom).

### Step 3 — Create the upload folders
```bash
mkdir -p backend/uploads/images
mkdir -p backend/uploads/reports
```

That's it for setup. Now every time you want to run the app:

---

## Running the App (Every Time)

You need TWO terminal windows open simultaneously.

### Terminal 1 — Start the Backend

```bash
# Navigate to the structguard folder
cd path/to/structguard

# Start Flask
python run.py
```

You should see:
```
=======================================================
  StructGuard AI Backend — Starting...
=======================================================
  API:      http://localhost:5000/api
  Demo accounts (all passwords: Demo1234!):
    supervisor@demo.com  → Site Supervisor
    developer@demo.com   → Developer/Owner
    inspector@demo.com   → Regulatory Inspector
    admin@demo.com       → Agency Administrator
=======================================================
```

**Keep this terminal open.** The backend must stay running.

### Terminal 2 (or VS Code Live Server) — Serve the Frontend

**Option A — VS Code Live Server (recommended):**
1. Open the `structguard/frontend/` folder in VS Code
2. Right-click `index.html` → "Open with Live Server"
3. Browser opens automatically at `http://localhost:5500`

**Option B — Python simple server:**
```bash
cd structguard/frontend
python -m http.server 5500
```
Then open `http://localhost:5500` in your browser.

---

## Demo Accounts

All passwords are `Demo1234!`

| Email | Role | What They See |
|---|---|---|
| `supervisor@demo.com` | Site Supervisor | Their projects, submit photos, view risk scores |
| `developer@demo.com` | Developer/Owner | Their projects, compliance status, PDF reports |
| `inspector@demo.com` | Inspector | All flagged projects, inspection queue, analytics |
| `admin@demo.com` | Agency Admin | Full dashboard, analytics, user management, stop-work orders |

**Try all 4 accounts** — each one shows a different screen because roles are enforced on the backend.

---

## What Each Role Sees

### Supervisor / Developer
- Dashboard with their project stats
- Projects list (only their own)
- Submit Photos form → AI analysis → Risk Score
- Download PDF report
- My Profile

### Inspector
- Dashboard with system-wide flagged count
- All projects (filtered by risk, status)
- Inspection Queue (AI-prioritised high-risk sites)
- Analytics dashboard

### Agency Admin (LASBCA Director level)
- Everything the Inspector sees, PLUS:
- User Management (deactivate/reactivate accounts)
- Issue Stop-Work Orders on projects

---

## AI Analysis — Demo vs Real

By default, the AI runs in **demo mode** (`.env` has `AI_DEMO_MODE=true`).
Demo mode returns realistic-looking fake risk analysis so you can test the full flow without an API key.

**To enable real AI analysis:**
1. Get an Anthropic API key: https://console.anthropic.com
2. Open `.env`
3. Set `ANTHROPIC_API_KEY=your-key-here`
4. Set `AI_DEMO_MODE=false`
5. Restart the backend

---

## Common Problems & Fixes

**Problem: "Cannot connect to server. Is the backend running?"**
- The backend isn't running. Start `python run.py` in Terminal 1.

**Problem: Login says "Invalid email or password"**
- Make sure the backend started successfully (check Terminal 1).
- Use exact demo credentials: password is `Demo1234!` (capital D, ends in !)

**Problem: CORS error in browser console**
- Open `.env`, check `FRONTEND_URL=http://localhost:5500`
- Make sure your frontend is on port 5500, not 3000 or another port.
- Restart the backend after any `.env` change.

**Problem: "Module not found" when starting backend**
- Run `pip install -r backend/requirements.txt` again.

**Problem: Database errors**
- Delete `structguard.db` and restart — Flask will recreate it with fresh demo data.

**Problem: Backend starts but shows no demo accounts**
- The database already exists with accounts. Use the demo credentials above.

---

## File Structure Reference

```
structguard/
├── HOW_TO_RUN.md          ← This file
├── .env.example           ← Copy to .env, fill in your values
├── .env                   ← Your config (never commit to GitHub!)
├── .gitignore             ← Tells Git what to ignore
├── run.py                 ← START THE BACKEND WITH THIS
│
├── backend/
│   ├── requirements.txt   ← Python packages to install
│   ├── app.py             ← Flask application factory
│   ├── models/
│   │   ├── user.py        ← User database model (roles, password hashing)
│   │   ├── project.py     ← Project/site model
│   │   └── submission.py  ← Photo submission + Report models
│   ├── routes/
│   │   ├── auth.py        ← /api/auth/* (login, register, me)
│   │   ├── projects.py    ← /api/projects/* (CRUD + stats)
│   │   ├── analysis.py    ← /api/analysis/* (photo upload + AI)
│   │   ├── reports.py     ← /api/reports/* (PDF generation + download)
│   │   └── admin.py       ← /api/admin/* (agency dashboard, users)
│   ├── services/
│   │   ├── ai_analysis.py ← AI risk detection engine (Claude Vision)
│   │   └── pdf_generator.py← PDF inspection report builder
│   └── utils/
│       └── auth.py        ← JWT helpers, role decorators
│
└── frontend/
    ├── index.html         ← OPEN THIS IN BROWSER (the whole app)
    ├── css/
    │   └── style.css      ← All styles (light + dark mode)
    └── js/
        ├── app.js         ← API client, auth, routing, theme
        └── pages.js       ← Each page's load/render logic
```

---

## For Version 2 — How to Extend

### Add a new page:
1. Add `<section id="page-yourpage" class="page">` in `index.html`
2. Add the route to `router.show()` in `app.js`
3. Add a page loader in `pages.js`

### Add a new API endpoint:
1. Add the route function to the relevant file in `backend/routes/`
2. Protect with `@jwt_required()` and `@require_role(...)` as needed

### Add a new database table:
1. Create a new model class in `backend/models/`
2. Import it in `backend/models/__init__.py`
3. Flask will create the table automatically on next start

### Add a new user role:
1. Add to the `Enum` in `backend/models/user.py`
2. Add the role's permission methods to `User`
3. Add to `authForms.register()` in `index.html`

---

## Deployment to Production (When Ready)

For deploying to a server (e.g. Render, Railway, DigitalOcean):

1. Change `.env`:
   - Strong `SECRET_KEY` and `JWT_SECRET_KEY`
   - `DATABASE_URL` → PostgreSQL connection string
   - `AI_DEMO_MODE=false`
   - Real `ANTHROPIC_API_KEY`

2. Use Gunicorn instead of the development server:
   ```bash
   pip install gunicorn
   gunicorn "backend.app:create_app()" --workers 4 --bind 0.0.0.0:$PORT
   ```

3. Serve the `frontend/` folder via a CDN or static hosting (Netlify, Vercel).

4. Update CORS `FRONTEND_URL` to your real domain.

---

*StructGuard AI | Team Spiro | UDARA Bootcamp 2025*
