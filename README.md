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

3. **Get a Gmail App Password**
   Requires 2-Step Verification on the Google account. Generate one at
   https://myaccount.google.com/apppasswords — this is what the script authenticates
   with, not your normal Gmail password.

4. **Configure environment**
   ```
   cp .env.example .env
   ```
   Fill in `CANVAS_BASE_URL`, `CANVAS_API_TOKEN`, `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`.
   `RECIPIENT_EMAIL` is optional and defaults to `GMAIL_ADDRESS`.

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
cloud-scheduled agent, with `CANVAS_BASE_URL`, `CANVAS_API_TOKEN`, `GMAIL_ADDRESS`, and
`GMAIL_APP_PASSWORD` registered as its secrets. Trigger it once on demand after setup to
confirm the cloud run works end-to-end before trusting the daily cadence.
