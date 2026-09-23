# FraudLens AI

**Finnovate Hackathon 2026 — Challenge 5: "FraudLens AI — Spot the Warning Signs Before You Pay"**
Sponsor: Clarity

Help people recognize suspicious financial messages before they send money, not by guessing with an AI model alone, but by checking the claimed sender against Mauritius' own official financial institution registries, then layering AI-driven explanation on top.

---

## The idea

Most "AI fraud detection" is a language model guessing whether something looks suspicious, a probability score with no real accountability behind it. FraudLens is built around a different, sharper claim:

"This claimed sender was not found in the Bank of Mauritius registry snapshot used by FraudLens" — a checkable fact against a specific, dated data source, not a guess.

A user pastes a suspicious message (an SMS, an email, a WhatsApp text) along with who it claims to be from. FraudLens checks that claimed sender against a locally-cached snapshot of Bank of Mauritius's list of licensed banks and financial participants, and the Financial Services Commission's licensed investment dealers and forex brokers, and immediately tells the user:

- Verified — the sender matches a real, currently-licensed institution in the registry snapshot
- Suspicious (not found) — the sender doesn't appear in the registry snapshot at all
- Suspicious (revoked) — the sender's name exactly matches a real entity, but that entity's license has been surrendered or revoked, a specific, sourced fact (real cases from actual FSC public notices)
- High risk (potential impersonation) — the sender's name closely resembles a real institution but doesn't exactly match it, a pattern worth treating with caution, similar to real cases Mauritius has seen (Bank of Mauritius's January 2026 alert about a fake "digital bank" using a near-identical name to a real one)

Independently, a deterministic indicator layer scans the message's own text — no AI required — for concrete red flags: requests for a one-time password or card details, urgency language, payment requests, investment-return promises, and any links. Critically, **registry verification does not mean a message is safe**: a message from a genuinely verified sender that also asks for an OTP still surfaces as high risk, since a real institution's name can be attached to a fraudulent message just as easily as a fake one. This is deterministic, explainable, and always available — no AI call required for either signal. An AI layer (not yet wired in) will add a third signal on top: reasoning about tone and context a regex can't reliably capture, informed by real, current 2026 fraud alerts from Bank of Mauritius, MCB, and Absa.

## Why this, and why now

Mauritius already has 89.8% financial inclusion, the highest in Africa. The problem isn't access, it's trust and verification. Cyber-enabled fraud, fake investment schemes, impersonated banks, fraudulent job offers, is now the most common financial crime type in the country, and Mauritius' Financial Crimes Commission reached over 94,500 people through fraud-awareness programmes in just a four-month period (Dec 2025 to Mar 2026). FraudLens is built to do programmatically, in seconds, what those awareness campaigns try to do manually at scale.

See `docs/research.md` for full sourcing.

## Current status

Backend: built and tested (107/107 automated tests passing). Auth/security, the registry-check feature (Bank of Mauritius + FSC data), the deterministic indicator-extraction layer, PII scrubbing, rate limiting, and a consolidated security test suite are complete and working end-to-end.

AI layer: intentionally not yet built — the registry and indicator layers already produce real, useful, explained verdicts entirely on their own. Local-only by design (no hosted APIs) for privacy and demo reliability — see "AI integration point" below.

Frontend: in `frontend/` — a Vite + React client (see `frontend/README.md`).

---

## Project layout

```
backend/
  app/
    main.py               - FastAPI entrypoint, middleware, router registration
    database.py            - SQLAlchemy engine/session setup (SQLite by default)
    models.py               - User, Check, RegistryEntity, and supporting auth tables
    schemas.py                - Pydantic request/response models
    security.py                 - password hashing, JWT creation/validation (with revocation)
    crypto.py                     - Fernet encryption for stored API keys
    login_guard.py                  - brute-force lockout on repeated failed logins
    audit_log.py                      - security-event logging
    password_reset.py                   - token-based password reset (logged, no email provider)
    email_verification.py                 - token-based email verification (tracked, not enforced)
    security_headers.py, error_handling.py, body_size_limit.py - hardening middleware

    entity_matcher.py      - THE CORE DIFFERENTIATOR: fuzzy-matches a claimed sender
                               name against the registry snapshot (verified / revoked /
                               name_mismatch / not_found)
    indicator_extractor.py    - deterministic text analysis: URLs, phone numbers, OTP/card
                                   requests, urgency, payment/investment language
    pii_scrubber.py              - regex-based masking of OTPs, card numbers, phone
                                      numbers, and emails before storage or any AI call
    verdict.py                      - combines the registry, indicator, and (once wired in) AI
                                          signals into a final safe / suspicious / high_risk verdict
    checks_rate_limit.py               - per-user fixed-window rate limiting on POST /checks
    registry_data.py                      - real registry snapshot data: Bank of Mauritius's
                                              participant list plus FSC-licensed investment
                                              dealers/forex brokers, known public aliases, and
                                              real dated revoked/surrendered entities
    registry_sync.py                         - loads registry_data.py into the database

    routers/
      auth.py                       - signup, login, password reset, email verification
      settings.py                     - API key mgmt, change password, delete account,
                                          session revocation, audit log
      checks.py                         - the core FraudLens feature endpoint

  tests/
    test_entity_matcher.py    - matcher algorithm tests (synthetic data)
    test_real_registry_data.py - tests against the REAL Bank of Mauritius and FSC data
    test_indicator_extractor.py - the deterministic text-analysis layer
    test_verdict.py            - the three-signal combination logic
    test_pii_scrubber.py       - PII masking
    test_checks.py            - end-to-end tests of the /checks endpoint
    test_checks_rate_limit.py - rate limiting on /checks
    test_security.py          - consolidated security checklist
    test_save_check_privacy.py - the save_check: false opt-out

  registry_data.py, .env.example, requirements.txt, pytest.ini

docs/
  research.md               - Mauritius fintech fraud research, sourced and dated
```

## Setup

```bash
cd backend
pip install -r requirements.txt --break-system-packages
cp .env.example .env
```

Edit `.env`:
- `JWT_SECRET_KEY` - any long random string
- `ENCRYPTION_KEY` - generate with:
  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```

Load the real registry data, then start the server:

```bash
python -m app.registry_sync
uvicorn app.main:app --reload
```

API docs: `http://localhost:8000/docs`

## Tests

```bash
pip install pytest --break-system-packages
pytest
```

190 tests, fully offline, no external network calls, across sixteen files. Beyond the entity-matcher and registry-data files described below, dedicated suites also cover: `test_url_fetcher.py` (SSRF protection for the URL-input mode), `test_ocr.py` (image-to-text extraction), `test_multi_input.py` (text/URL/image all converging on the same pipeline), `test_domain_analyzer.py` and `test_phone_analyzer.py` (lookalike-domain and mismatched-phone-number detection), `test_feedback.py` (the correct/incorrect verdict feedback loop), and `test_repeat_sender.py` (per-user history of past checks on the same claimed sender).

- `test_entity_matcher.py` / `test_real_registry_data.py` — the matching algorithm and its behavior against real Bank of Mauritius and FSC data. Between them, these two files caught and fixed six real bugs during development:

1. The default fuzzy-matching scorer (WRatio) falsely matched unrelated institution names sharing common words like "Bank", the real fake "Tranz Digital Bank" entity (from Bank of Mauritius's actual alert) scored 85% against an unrelated real bank. Fixed by switching scorers.
2. Even after that fix, a 95% "verified" threshold let a single-character typo ("Absaa Bank" vs "Absa Bank") pass as fully verified. Fixed by raising the threshold.
3. Common public abbreviations ("MCB", "HSBC", "SBM") didn't reliably match their much longer formal legal names in the registry. Fixed by loading known aliases as additional searchable entries.
4. Short legitimate names sharing a common word could trigger a false "impersonation" flag against a different real entity ("Absa Bank" scoring high against "AfrAsia Bank Limited"). Fixed with a minimum claim-length guard before allowing that classification.
5. The same alias gap resurfaced with FSC data: the globally-recognized brand "FXTM" didn't match its formal licensed entity name "Exinity Limited". Fixed the same way as #3.
6. A real, dated FSC notice about a surrendered license ("Trade T Capital Markets") was initially only loaded as data but never actually wired into the sync pipeline or the matcher's status branching — an exact name match to a no-longer-active entity was silently reported as if it were fully verified. Fixed by adding a distinct `revoked` status, surfaced with the specific sourced detail.

All six are now permanent regression tests.

- `test_indicator_extractor.py` — the deterministic text-analysis layer (URLs, phone numbers, OTP/card requests, urgency, payment/investment language). Caught one real precision bug: a message merely *containing* the word "OTP" (e.g. a bank legitimately notifying someone of their own one-time code) was flagged identically to a message actively *requesting* one — opposite situations. Fixed by requiring a request verb near the mention.
- `test_verdict.py` — the three-signal combination logic (registry + indicators + AI). Directly tests the property this project is built around: a verified sender combined with an OTP request must still surface as `high_risk`, not be diluted by the clean registry result.
- `test_pii_scrubber.py` — regex-based PII masking. Caught two real bugs: sequential regex passes corrupting each other's output (an OTP pattern re-redacting digits inside an already-masked card placeholder), and a greedy trailing-separator match eating whitespace after a masked card number.
- `test_checks.py` — end-to-end tests of the `/checks` endpoint (registry statuses, verdicts, per-user isolation, filtering, PII scrubbing through the real pipeline).
- `test_checks_rate_limit.py` — the per-user fixed-window rate limiter on `/checks`.
- `test_security.py` — a consolidated security checklist: malformed/wrong-secret/nonexistent-user/revoked JWTs, single-use password reset tokens, login lockout, oversized-request rejection, API key exposure and encryption-at-rest, audit log content, unhandled-exception detail leakage, and a prompt-injection boundary test confirming message content has no path to influence the registry verdict.
- `test_save_check_privacy.py` — the `save_check: false` option, confirming an unsaved check is never written to the database at all.

## API reference

- `POST /auth/signup`, `POST /auth/login`, `GET /auth/me`
- `POST /auth/password-reset/request`, `GET .../verify`, `POST .../confirm`
- `POST /auth/verify-email/confirm`, `POST /auth/verify-email/resend`
- `GET/POST/DELETE /settings/api-key`, `GET /settings/audit-log`
- `POST /settings/revoke-sessions`, `POST /settings/change-password`, `POST /settings/delete-account`
- `POST /checks/` - submit a message plus claimed sender, get back a registry-checked verdict. Pass `save_check: false` to get the analysis without it being persisted. Rate-limited to 20 requests per 5 minutes per user.
- `GET /checks/`, `GET /checks/{id}` - list/retrieve past checks (own only, per-user isolated)
- `GET /health`

## AI integration point

The AI layer is deliberately not built yet — the registry and indicator layers are complete, working features entirely on their own. When ready, it plugs into exactly one place: the `# AI HOOK` comment inside `app/routers/checks.py`'s `create_check()` function. The `Check` model, schema, and `verdict.py`'s combination logic are already built to accept an AI signal (`ai_risk_score`, `ai_flags`, `ai_explanation`) alongside the registry and indicator signals — wiring in the AI call should not require restructuring anything that already exists.

**Local-only by design, no hosted APIs.** This is a deliberate choice, not just a constraint: message content may contain OTPs, account fragments, or private conversation text (mitigated but not eliminated by `app/pii_scrubber.py`), and running inference locally means that content genuinely never leaves the machine, rather than depending on a third party's data-handling promises. It also removes network dependency and API cost/rate-limit risk during a live demo — directly relevant given the jury's stated emphasis on demo reliability.

Planned approach: a locally fine-tuned model (Mistral 7B or Llama 3.1 8B, QLoRA, run on a 12GB-VRAM machine) analyzing message text for scam language patterns and tone — reasoning that complements, rather than re-derives, what the indicator layer already establishes deterministically (the AI layer should be told what the indicator layer already found, not asked to rediscover it from scratch).

## Security & privacy

FraudLens treats every layer of input as untrusted, and keeps the deterministic registry check structurally independent of anything a submitted message says:

- User-submitted messages are untrusted input and are never executed or given any path to influence the registry verdict — confirmed directly in `tests/test_security.py`'s prompt-injection boundary test.
- Registry results are computed purely from the claimed sender against the database; message *content* has no way to change `registry_match_status`, even once an AI layer is added.
- Passwords are hashed with bcrypt; JWTs carry `exp`/`iat` and are checked against a per-user revocation timestamp (`tokens_valid_after`) so "log out everywhere" and a password change/reset immediately invalidate every prior token.
- API keys are encrypted at rest (Fernet) and never returned in plaintext after saving — only a masked preview.
- Password reset and email verification tokens are stored hashed (SHA-256), single-use, and time-limited — never the raw token.
- Failed logins are rate-limited with a lockout (5 failures / 15 min), keyed by email so it behaves identically for unknown addresses (no account-existence leak).
- `/checks` itself is rate-limited per user (20 / 5 min) to prevent automated abuse of the core feature.
- Users can only ever access their own checks — enforced at the query level, tested directly for both existing checks and JWTs referencing deleted/nonexistent users.
- A dedicated `POST /checks` option, `save_check: false`, lets a user get a full analysis of a sensitive message (one containing an OTP, account number, or private conversation content) **without it ever being written to the database** — not saved-then-deleted, genuinely never persisted. See `tests/test_save_check_privacy.py`.
- The global exception handler guarantees no internal error detail (paths, stack traces, exception types) ever reaches a client response.

See `tests/test_security.py` for the executable version of this list.

## Responsible use

FraudLens is a verification and assistance tool, not a guarantee that a message is legitimate or fraudulent. A registry match confirms the claimed sender's name is in a specific, dated snapshot — it does not confirm the message itself is genuine, since even a real institution's name can be attached to a fraudulent message. Conversely, a sender not found in the snapshot is not proof of fraud — many legitimate senders (couriers, retailers, individuals) are outside its scope entirely. Users should independently verify anything urgent or financial through an institution's official channels — not a phone number or link contained in the message being checked — before transferring money or sharing credentials.



## Known limitations (honest, by design for a 3-day build)

- Known official domains and phone numbers (used by the domain and phone mismatch checks) are small, hand-curated tables covering a handful of major institutions, not exhaustive coverage. One phone number in this table was found during testing to be both a data-entry typo AND, once corrected, still unsourced/fabricated — it was removed rather than guessed at again. Every remaining entry is tied to a real, checkable source citation.

- Registry snapshot is a hand-curated, real, sourced set of well-known entities across Bank of Mauritius's participant list (banks, leasing, insurance, microfinance, P2P, utility bodies) and FSC-licensed investment dealers/forex brokers — not a scrape of either regulator's full register, which runs to hundreds of entries across many license categories. Entries and known aliases are added as specific real-world cases are found; see `app/registry_data.py`'s comments for exactly what's covered and why each entry was chosen.
- Registry data is a periodically-synced snapshot, not a live query against the source sites — appropriate for demo reliability, but needs a real refresh cadence in any actual deployment.
- The `revoked` registry status (a real, sourced fact about a specific entity's license having been surrendered or revoked) is currently only reflected in the free-text explanation shown to the user — the structured detail isn't yet its own field on the stored `Check` record or `CheckOut` response, so it can't be filtered/queried on independently. A reasonable next addition, not done here to avoid a mid-hackathon schema migration for a single field.
- No AI/local model layer yet — see "AI integration point" above; the deterministic registry and indicator layers are complete and already produce real, useful verdicts on their own.
- PII scrubbing is regex-based pattern detection for common, structurally-recognizable identifiers (OTP-shaped codes, card numbers, phone numbers, emails) — not a general PII-detection model, and not a guarantee every form of sensitive data is caught. `save_check: false` remains the stronger guarantee for a message a user knows contains something specific they don't want stored at all.
- Email verification and password reset both log their tokens/links server-side rather than sending real email, since no email provider is configured — clearly labeled in logs as a stand-in, not a real send.
