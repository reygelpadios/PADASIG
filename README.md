# PADASIG - Django foundation and first live dashboard

This is the Django application, separate from `padasig-prototype`. It has PostgreSQL models, Django admin, fake data, working senior authentication screens, and a read-only dashboard at `/portal/`. Login, a short loading screen after successful authentication, forced password change, privacy acceptance, logout, rate limiting, and idle expiry are implemented. PDF extraction, SMS, chat, and the remaining senior screens are not connected yet.

See [STEP_2_GUIDE.md](STEP_2_GUIDE.md) for the screen walkthrough, editing guide, security checks, and remaining work.

PADASIG displays staff-verified inclusion records. It does not calculate eligibility.

## What has already been done on this Mac

- Created `.venv` using Python 3.13.
- Installed Django 5.2 LTS, psycopg, and python-decouple.
- Created PostgreSQL database `padasig_dev` and applied migrations.
- Generated a private local `.env` with a random development secret.
- Loaded the fake demo records. No personal staff administrator password was chosen for you.

## Run it

Open Terminal and enter:

```bash
cd "/Users/macbookpro/Documents/Codex/2026-10-11/referenced-chatgpt-conversation-this-is-an/outputs/padasig-backend"
source .venv/bin/activate
python manage.py createsuperuser
```

Choose your own staff username and password. Email is optional. Password characters do not appear as you type. This staff account does not need a Senior ID.

Then start the server:

```bash
python manage.py runserver 127.0.0.1:8000
```

Open http://127.0.0.1:8000/login/ for senior login or http://127.0.0.1:8000/admin/ for staff administration. If that port is in use, use `127.0.0.1:8001` instead. Keep Terminal open while using the server. Stop with Control+C. Create a superuser only if you do not already have one. The homepage redirects to senior login.

## File map

```text
padasig-backend/
  manage.py                Runs Django commands
  requirements.txt         Allowed dependency versions
  requirements-lock.txt    Exact versions verified on this Mac
  setup_local.py           Generates .env once; never overwrites it
  .env.example             Configuration template without a real secret
  .env                     Local settings; private and ignored by Git
  config/
    settings.py            PostgreSQL, authentication, language, time zone
    urls.py                Staff admin and senior account routes
    wsgi.py                Django application entry point
  accounts/
    models.py              Credentials, senior profiles, proxies, requests, audit log
    validators.py          Senior ID normalization and validation
    backends.py            Staff username and senior-ID password checking
    views.py               Login, password setup, privacy, dashboard, help, logout
    middleware.py          First-time gates and senior idle expiry
    security.py            Database-backed failed-login counters
    urls.py                Senior screen addresses
    templates/accounts/    Shared layout and screen HTML
    static/accounts/       One CSS file, one JS file, supplied images
    forms.py               Admin form for creating a senior and hashed password
    admin.py               Basic account administration
    migrations/            Database schema history; created before first migrate
    tests.py               Account, authentication, and admin checks
    test_dashboard.py      Dashboard privacy and display-state checks
    templates/accounts/loading.html  Success-only loading screen
  benefits/
    models.py              Benefit program catalog
    admin.py               Basic benefit administration
    migrations/            Benefit schema history
  announcements/
    models.py              Posts, verified inclusion records, read receipts
    admin.py               Basic post/inclusion administration
    migrations/            Announcement schema history
    management/commands/
      seed_demo.py         Repeatable fake data and demonstration modes
    tests.py               State, record validation, and seeding checks
```

## Account design decision

The approved staff/senior separation changes the original proposed `Senior(AbstractBaseUser)` design:

- `accounts.User(AbstractUser)` holds hashed passwords, usernames, activity flags, permissions, creation date, and last login. This is `AUTH_USER_MODEL`, created in the first migration.
- `Senior` is a one-to-one profile holding the five-digit ID and the senior-specific fields. Staff accounts have no senior profile.
- Senior IDs are text, unique, and indexed. Database validation requires five ASCII digits. The configurable regex adds validation; changing the ID length later requires a schema migration too.
- Senior public authentication uses `authenticate(senior_id=..., password=...)`. Their internal username is not accepted by the staff username backend.
- Only staff usernames can authenticate through the username backend. Normal seniors cannot access Django admin.
- First-login password and consent flags are enforced server-side in senior routes. Staff password resets require another senior password change.
- The static prototype's `largest` setting maps to the database's `xlarge` value. Setup screens respect the stored preference; the profile editor comes later.

## Admin tasks

Use **Seniors -> Add** to create a senior profile and its login account together. Enter a five-digit ID, fake name, and initial password. Passwords are hashed, `must_change_password` is true, and consent acceptance is empty.

For an optional default initial password during local development, set `INITIAL_SENIOR_PASSWORD` in `.env`. It is blank by default so staff must enter a password. Do not use the demo shared password for real accounts.

**Users** provides Django's standard staff permissions and password administration. Prefer creating senior accounts through **Seniors**, not **Users**.

Inclusion records can be entered manually by authorized staff for main posts only. The reviewing staff account and update date are recorded automatically. Each admin inclusion change also adds a ChangeLog event. Future PDF extraction must stop at a review screen and must not create confirmed records automatically.

Contact-change requests, correction requests, read receipts, and audit logs are visible but read-only in admin. Their workflow will come later. Pending contact requests do not modify the existing mobile/proxy details.

## Display-state rules

`Announcement.objects.active_main()` selects published main posts whose publication date has arrived and whose payout date is today or later, using Asia/Manila local time. A null payout date means unscheduled, so it is not active under this rule.

`Announcement.objects.not_in_list(senior)` returns those active posts without an inclusion record for that senior. The dashboard shows **Makipag-ugnayan sa OSCA**, not a conclusion about eligibility. Any inclusion status, including pending, means an inclusion record exists.

`Announcement.objects.no_active_benefit()` is true when no such main post exists. Reminders never count as active benefits and never carry inclusion records. `Benefit.is_active` is a catalog flag; it is not an eligibility rule or an extra date filter.

The dashboard at `/portal/` reads only published active main posts and the signed-in senior's own inclusion records. It shows multiple benefits, included/pending/claimed states, payout details and text-only requirements where appropriate, a next-step message, and the latest public announcement. Missing records display **Makipag-ugnayan sa OSCA**. An expired public post may still appear as the latest announcement, but not as an active benefit. Beneficiary PDFs are never linked there. The five navigation labels are present; only Dashboard is active while the other four screens await later stages.

The status label's **Updated by OSCA on [date]** uses `InclusionRecord.updated_at`. A missing record has no status date to invent. `Announcement.updated_at` is for changes to the post itself. The extra `InclusionRecord.updated_by` field records the staff member responsible for the status. The dashboard language and text-size controls work; text size is saved to the senior profile.

Amounts, valid payout time pairs, valid Senior IDs, unique inclusion/read rows, and one pending contact request per field have database constraints. Main-post-only and staff-only relations are checked by model saves and database triggers. Do not write directly to the database in future workflows; use validated model saves and explicit staff confirmation so audit events are recorded as well.

## Fake data and checks

All sample people, IDs, contacts, and venues are fictional. Senior `10001` is Lourdes M. Santos; all three proxies have different names from their seniors. The values in the static prototype were left unchanged. Fake phone numbers deliberately contain X characters and cannot receive messages.

Run again safely:

```bash
python manage.py seed_demo
python manage.py check
python manage.py test accounts announcements --noinput
```

Repeated seeding does not duplicate rows or reset existing passwords. It refreshes the demo posts and inclusion statuses. It refuses to overwrite conflicting non-demo senior IDs and refuses to run when `DEBUG=False`. `demo_seed_staff` is a non-login authoring account with an unusable password, not your administrator login.

Demo senior passwords initially use `DEMO_PASSWORD` from `.env`, default `ChangeMe123!`. These are local fake accounts only. After changing a demo password through setup, use the new password: seeding never resets it.

| Senior ID | Demonstration |
| --- | --- |
| 10001 | Multiple: included in Pamaskong Handog; pending in Wellness Support |
| 10002 | Included |
| 10003 | Pending |
| 10004 | Claimed |
| 10005 | No inclusion record; contact OSCA display state |
| 10006 | Included in Birthday Incentive |
| 10007 | Claimed Birthday Incentive |
| 10008 | Multiple included benefits |

There are 3 benefits, 4 announcements, 8 seniors, 3 proxies, and 9 inclusion records. Read receipts exist for a few posts; a missing receipt means unread.

The reference seed uses the exact October-December 2026 dates from the brief. To demonstrate no active benefit, change only the seeded main-post payout dates:

```bash
python manage.py seed_demo --demo-no-active
```

Restore the original dates with `python manage.py seed_demo`. After the reference dates expire, use `python manage.py seed_demo --relative-dates` to shift publication and payout dates together relative to today. Neither option touches non-demo posts.

## New-machine setup

Install supported Python and PostgreSQL first, then from this folder run:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python setup_local.py
createdb -h 127.0.0.1 -U YOUR_LOCAL_POSTGRES_ROLE padasig_dev
```

Edit `.env` with your local PostgreSQL username, host, and password. The included Mac defaults use the Homebrew local role `macbookpro`, localhost, port 5432, and no database password. These are development settings only. Then run `python manage.py migrate`, `python manage.py seed_demo`, and `python manage.py createsuperuser`.

For future model edits, run `python manage.py makemigrations` and then `python manage.py migrate`. Do not delete or edit applied migrations to change the schema.

## Foundation Checklist

- PostgreSQL responds and migrations are applied.
- `/admin/` accepts your staff account.
- Senior creation stores a hashed password and first-login flags.
- Demo records and all listed display states can be inspected in admin/data.
- Tests and Django checks pass.
- The static prototype still opens independently.

Step 2 adds Django login and first-time setup, generic login errors, five-failure/15-minute login cooldowns, and a 10-minute senior idle timeout. The first read-only Django dashboard is now connected. The remaining user screens, private PDF workflow, contact approval, and production deployment remain future work. No real senior data should be entered yet. The privacy notice is a development draft, not a claim of legal compliance.

After a successful returning-senior login, `/login/loading/` displays a one-time 1.5-second logo animation, then opens `/portal/`. A first-time senior still completes password setup and privacy acceptance before seeing it. Wrong passwords never show it. Adjust `FILL_MS`, `HOLD_MS`, and `FADE_MS` at the top of `accounts/static/accounts/portal.js`; the script passes these durations to the CSS animation. Reduced-motion mode uses a shorter fade instead of a moving wave. The static prototype `index.html` is unchanged because it has no authenticated login.
