# Running the merged project

This repo now contains both halves side by side, as `README.md` describes:

```
backend/    FastAPI API (auth, registry check, checks history)
frontend/   Vite + React client (Klaro UI)
```

They're already wired to talk to each other on their default ports —
no path or port changes were needed.

## 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# .env is already present with working dev values (SQLite + a Fernet key).
# Rotate JWT_SECRET_KEY and ENCRYPTION_KEY before any real deployment.
uvicorn app.main:app --reload --port 8000
```

`fraudlens.db` is included with the registry already synced, so you don't need
to run `registry_sync` again unless you want to refresh it.

## 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_BASE already points at http://localhost:8000
npm run dev
```

Opens on `http://localhost:5173`, which matches the backend's
`FRONTEND_ORIGIN` default — CORS just works.

## Getting an account

There's no seeded demo user. Login isn't gated on email verification (it's
only tracked, not enforced), so the fastest path in is:

1. Go to `http://localhost:5173/signup`, create an account with any email/password.
2. You're logged in immediately — no need to click a verification link.

If you'd rather have a ready-made account without touching the signup form,
say the word and I'll add a small seed script that inserts a pre-verified
user straight into `fraudlens.db`.

## 3. Admin dashboard

A SIEM-style admin console lives at `http://localhost:5173/admin` —
live system stats, a cross-user check explorer, user management
(promote/suspend), and a real-time security event feed (Server-Sent
Events), all behind the same login as the regular app: an account
just needs `role = "admin"` to see the "Admin console" link in the
sidebar and get past `/admin`'s route guard.

**Getting in the first time:** the earliest-registered account in
`fraudlens.db` is promoted to admin automatically the first time the
backend starts with the new `role`/`is_active` columns (see
`app/migrations.py`) — so if you already have an account from before,
just log back in and you'll see the "Admin console" link. On a
completely fresh database, sign up once as normal; that first account
becomes the admin.

To promote a *different* or additional account later, either use the
admin panel itself (Users → Promote) once you have one admin, or run:

```bash
cd backend
python -m app.promote_admin someone@example.com
```

A suspended user's existing sessions are killed immediately (same
mechanism as "log out everywhere"), not just blocked on next login.
