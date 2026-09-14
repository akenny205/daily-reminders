# Homework Reminder

Sends a daily email digesting your outstanding Canvas assignments, soonest-due first.
Overdue work is called out at the top; everything else is sorted by due date within the
next 14 days (see `DEFAULT_LOOKAHEAD_DAYS` in `src/aggregator.py`).

Gradescope is intentionally out of scope for now — it has no public API and its login
goes through school SSO/MFA, which can't be scripted daily without a persisted browser
session. Revisit later if wanted.

## Setup

1. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

2. **Get a Canvas API token**
   In Canvas: Account → Settings → "+ New Access Token". Copy the base URL of your
   Canvas instance too (e.g. `https://northeastern.instructure.com`).

3. **Get a Resend API key**
   Sign up at https://resend.com and create an API key. Email is sent over a plain
   HTTPS POST rather than SMTP, since some environments this runs in (cloud-scheduled
   runs especially) only allow HTTP(S) traffic out, not raw SMTP sockets. Using the
   shared `onboarding@resend.dev` sender needs no domain verification, but only
   delivers to the email address you signed up to Resend with.

4. **Configure environment**
   ```
   cp .env.example .env
   ```
   Fill in `CANVAS_BASE_URL`, `CANVAS_API_TOKEN`, `RESEND_API_KEY`, `RECIPIENT_EMAIL`.

5. **Dry run** (prints the digest instead of emailing it — safe to run repeatedly)
   ```
   python main.py --dry-run
   ```

6. **Send for real**
   ```
   python main.py
   ```

## Scheduling

Runs via GitHub Actions (`.github/workflows/daily-digest.yml`) on a daily cron, plus a
manual `workflow_dispatch` trigger for on-demand runs from the repo's Actions tab.

Add these as repo secrets (Settings → Secrets and variables → Actions → New repository
secret): `CANVAS_BASE_URL`, `CANVAS_API_TOKEN`, `RESEND_API_KEY`, `RESEND_FROM`,
`RECIPIENT_EMAIL` — same values as your local `.env`.

(This previously ran as a Claude Code cloud routine. That worked, but consumed Claude
usage on every run and needed a workaround for SMTP since that sandbox only proxies
HTTP(S) traffic — GitHub Actions runners have normal outbound network access and cost
nothing for a job this small, so it moved here instead.)
