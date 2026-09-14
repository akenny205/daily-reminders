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

Use Claude Code's `schedule` skill to run `python main.py` in this repo once a day as a
cloud-scheduled agent, with `CANVAS_BASE_URL`, `CANVAS_API_TOKEN`, `RESEND_API_KEY`, and
`RECIPIENT_EMAIL` registered as environment variables on the routine's environment.
Trigger it once on demand after setup to confirm the cloud run works end-to-end before
trusting the daily cadence.

Note: the cloud sandbox only proxies HTTP(S) traffic — raw SMTP sockets fail with
`OSError: [Errno 97] Address family not supported by protocol` regardless of the
environment's network access setting. That's why this sends mail via Resend's HTTPS
API instead of SMTP.
