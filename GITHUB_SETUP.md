# StructGuard AI — GitHub Setup Guide
**How to push your project to GitHub securely**

---

## Why GitHub?
GitHub stores your code safely in the cloud, lets your team collaborate,
and is how you'll eventually deploy to a real server. Do this once and
your whole team can pull the latest code.

---

## Step 1 — Create a GitHub Account (if you don't have one)
Go to https://github.com and sign up. Free tier is fine.

---

## Step 2 — Create a New Repository on GitHub

1. Click the **+** button (top right) → **New repository**
2. Fill in:
   - **Repository name:** `structguard-ai`
   - **Description:** `Construction site safety monitoring platform`
   - **Visibility:** Private (recommended — keeps your code hidden)
   - **DO NOT** tick "Add a README" or "Add .gitignore" — you already have these
3. Click **Create repository**
4. GitHub will show you a page with commands — keep that tab open

---

## Step 3 — Connect Your Local Folder to GitHub

In Git Bash inside your `Structguard` folder, run these one at a time:

```bash
# Tell Git who you are (use your GitHub email)
git config --global user.name "Your Name"
git config --global user.email "your@email.com"

# Connect your folder to the GitHub repo you just created
# Replace YOUR_USERNAME with your actual GitHub username
git remote add origin https://github.com/YOUR_USERNAME/structguard-ai.git

# Check the .gitignore is working (you should NOT see .env in this list)
git status
```

---

## Step 4 — Check .env is Protected

This is the most important step. Run:

```bash
cat .gitignore | grep ".env"
```

You should see `.env` listed. This means your secret keys will never
be uploaded to GitHub. If you don't see it, run:

```bash
echo ".env" >> .gitignore
```

---

## Step 5 — Stage and Push Your Code

```bash
# Stage all files
git add .

# Check what's being committed — make sure .env is NOT listed
git status

# Create your first commit
git commit -m "feat: initial StructGuard AI implementation"

# Push to GitHub
git push -u origin master
```

If Git asks for your username and password:
- Username: your GitHub username
- Password: use a **Personal Access Token** (not your GitHub password)
  → Go to GitHub → Settings → Developer Settings → Personal Access Tokens → Generate new token
  → Tick "repo" scope → Copy the token → paste it as your password

---

## Step 6 — Verify on GitHub

Open `https://github.com/YOUR_USERNAME/structguard-ai` in your browser.
You should see all your files — but NOT the `.env` file. That stays local only.

---

## For Your Team — How They Clone and Run It

Each team member runs:

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/structguard-ai.git
cd structguard-ai

# Create their own .env from the example
cp .env.example .env
# (they edit .env with their own settings if needed)

# Install packages
pip install -r backend/requirements.txt

# Create upload folders
mkdir -p backend/uploads/images backend/uploads/reports

# Run
python run.py
```

---

## Daily Workflow — Keeping Code in Sync

```bash
# Pull latest changes from teammates
git pull

# After you make changes, push them
git add .
git commit -m "fix: description of what you changed"
git push
```

---

## What Gets Uploaded vs What Stays Local

| File/Folder | Goes to GitHub? | Why |
|---|---|---|
| `backend/` | ✅ Yes | Your Python code |
| `frontend/` | ✅ Yes | Your HTML/CSS/JS |
| `run.py` | ✅ Yes | Server starter |
| `.env.example` | ✅ Yes | Template (no secrets) |
| `.gitignore` | ✅ Yes | Tells Git what to skip |
| `HOW_TO_RUN.md` | ✅ Yes | Documentation |
| `.env` | ❌ NO | Contains your secret keys |
| `structguard.db` | ❌ NO | Local database |
| `backend/uploads/` | ❌ NO | User-uploaded photos |
| `.venv/` | ❌ NO | Python environment |

---

## Security Summary — What Was Fixed This Session

| Issue | Before | After |
|---|---|---|
| Demo passwords in HTML | `Demo1234!` written in plain HTML for everyone to read | Hidden in memory, only shown on localhost |
| Demo buttons | Always visible to anyone | Auto-hidden on real/deployed domain |
| `.env` on GitHub | Risk of being committed | `.gitignore` blocks it permanently |

---

*StructGuard AI — Team Spiro — UDARA Bootcamp 2025*
