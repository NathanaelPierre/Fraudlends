# CipherLab frontend

A Vite + React client for the CipherLab FastAPI backend (`../backend`). Talks to the
API with a plain `fetch` client — no framework beyond React Router — so it stays easy
to hand off or extend.

## Design concept

The app borrows its visual language from the thing it actually does: checking a
name against an official record. The interface reads as a case file — parchment
background with faint ledger rules, a blue "pen" color reserved for anything you can
click, and a rubber-stamped verdict (Verified / Unverified / High risk) as the one
graphic moment in the whole app. Everything else — forms, tables, settings — stays
quiet on purpose so that stamp means something when it lands.

## Run it

```bash
npm install
cp .env.example .env   # point VITE_API_BASE at your backend if it's not localhost:8000
npm run dev
```

This starts the dev server on `http://localhost:5173`. Make sure the backend's
`FRONTEND_ORIGIN` env var matches that origin (it does by default) so CORS allows
the requests, and that you've run `python -m app.registry_sync` and started uvicorn
first.

## Pages

- `/` — the core tool: paste a message + claimed sender, get a stamped verdict
- `/case-log` — saved checks, filterable by verdict
- `/case-log/:id` — a single saved check
- `/settings` — API key, password, sessions, audit log, account deletion
- `/login`, `/signup`, `/forgot-password`, `/reset-password`, `/verify-email` — auth flows,
  matching the backend's token-based reset/verification endpoints

## Notes

- `save_check: false` on the Check page is wired straight to the backend's
  never-persisted option — unchecking it means the result you see is never written
  to the database.
- The explanation and registry fields rendered on a result come directly from
  `CheckOut` (`ai_explanation`, `registry_match_status`, `registry_matched_entity`,
  `registry_match_score`, `explanation_source`) — nothing is inferred client-side.
- No component here assumes the AI layer exists yet; `explanation_source` is shown
  as "Registry only" today and will read "Registry + AI" automatically once the
  backend's `AI HOOK` is filled in.
