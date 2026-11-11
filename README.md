# Django Web Application for Sending SMS (Twilio)

**Course:** IT 120 – Integrative Programming and Technologies  
**Semester:** 1st Sem SY 2026–2027  
**Title:** Django Web Application for Sending SMS (Twilio)

A Django web app that lets a user enter a recipient phone number and message, validates input (including E.164 format), sends SMS through the Twilio Messages API, and shows clear success or error feedback. Send attempts are stored in SQLite and shown as message history. A live character counter helps keep messages within typical SMS length.

> **Important:** A successful send means the message was **submitted/queued** with Twilio. It does **not** by itself prove that the recipient’s handset has already received (delivered) the SMS.

---

## Group members and responsibilities

| Member | Responsibilities |
|--------|------------------|
| **Member 1** *(replace with name)* | Django project setup, views, URLs, application logic |
| **Member 2** *(replace with name)* | UI, forms, validation, user feedback |
| **Member 3** *(replace with name)* | Twilio integration, testing, documentation, demonstration |

---

## Main features

1. **SMS compose form** — recipient phone number, message textarea, Send SMS button (CSRF-protected).
2. **Input validation** — rejects empty phone, empty message, and non–E.164 numbers (e.g. requires `+639171234567`).
3. **Twilio send** — calls the Twilio Messages API when credentials are configured.
4. **User feedback** — Django messages for success (queued/submitted) or failure; field errors next to inputs.
5. **Safe error handling** — missing credentials, provider rejection, and network failures; secrets are never shown in the UI.
6. **SMS history** — each attempt saved (`to`, `body`, `status`, Twilio SID if any, error detail, timestamp); recent list on the home page and a dedicated History page.
7. **Live character counter** — client-side counter with ~160-character SMS segment hint.
8. **Demo / local fallback** — `DEMO_MODE=true` validates and records a simulated queued send without calling Twilio; if credentials are missing and demo is off, the app still runs and shows a friendly configuration error.

---

## Technologies and dependencies

| Technology | Role |
|------------|------|
| Python 3 | Runtime |
| Django 5.2 | Web framework |
| Twilio Python SDK | SMS Messages API |
| python-dotenv | Load `.env` configuration |
| SQLite | Local message history |
| Bootstrap 5 + custom CSS | UI |
| HTML / vanilla JS | Templates and character counter |

Pinned packages: see `requirements.txt` (generated from `pip freeze`).

---

## Project structure

```
Group Lab/
├── manage.py
├── requirements.txt
├── .env.example          # placeholders only — never real secrets
├── .gitignore
├── README.md
├── sms_project/          # Django project (settings, urls, wsgi/asgi)
└── sms_app/              # App: models, forms, views, services, templates, static
```

---

## Installation and setup

### 1. Create and activate a virtual environment

**Windows (PowerShell):**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
copy .env.example .env
```

On macOS/Linux: `cp .env.example .env`

Edit `.env` (do **not** commit this file):

```env
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
SECRET_KEY=django-insecure-change-me
DEBUG=True
DEMO_MODE=false
```

### 4. Run migrations

```bash
python manage.py migrate
```

### 5. Start the development server

```bash
python manage.py runserver
```

Open **http://127.0.0.1:8000/**

---

## Twilio configuration

1. Create a Twilio account and obtain **Account SID**, **Auth Token**, and a Twilio phone number.
2. Put them in `.env` (see `.env.example`). Never hardcode credentials in source files.
3. On a **Twilio trial** account, you can usually only send to **verified** recipient numbers.
4. Restart `runserver` after changing `.env`.

### Behavior matrix

| Condition | What happens |
|-----------|----------------|
| Valid credentials + `DEMO_MODE=false` | Real Twilio API send; history status `queued` on success |
| `DEMO_MODE=true` | No Twilio call; validates form; history status `demo`; success message says demo/queued simulation |
| Credentials missing/placeholder + `DEMO_MODE=false` | Form still validates; friendly error asking to configure `.env` or enable demo; history status `failed` |

Banner on the page warns when Twilio is not configured or when demo mode is on.

---

## How to run (quick)

```powershell
.\venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py runserver
```

- Compose / send: http://127.0.0.1:8000/  
- Full history: http://127.0.0.1:8000/history/

Optional admin: `python manage.py createsuperuser` then http://127.0.0.1:8000/admin/

---

## Testing procedures and expected results

Use the browser form (or Django test client). Keep `DEMO_MODE=true` for local demos without Twilio; set real credentials for a live send.

| # | Test case | Steps | Expected result |
|---|-----------|-------|-----------------|
| 1 | Valid phone + message (demo) | Set `DEMO_MODE=true`. Submit `+639171234567` and a non-empty message. | Success flash: demo / queued simulation. History row with status **Demo**. No Twilio call. |
| 2 | Valid phone + message (live) | Real Twilio creds, `DEMO_MODE=false`, verified recipient if trial. | Success flash: **submitted/queued** (not “delivered”). History **Queued / Submitted** with SID. |
| 3 | Empty phone | Leave phone blank; fill message; submit. | Field error: phone required / invalid. Flash: fix errors. No Twilio call. |
| 4 | Empty message | Fill valid phone; leave message blank; submit. | Field error: message required. No Twilio call. |
| 5 | Invalid phone | e.g. `09171234567` or `abc`; valid message. | Field error requiring E.164 (`+` and country code). |
| 6 | Missing credentials | Placeholders in `.env`, `DEMO_MODE=false`; valid form submit. | Friendly error to set `.env` or enable demo. **No** Account SID/Auth Token shown in UI. History **Failed**. |
| 7 | Character counter | Type in the message box. | Live count updates; ~160-char segment hint; over-160 styling. |

### Verification notes (this submission build)

Manual checks performed during development:

- App starts with `python manage.py runserver` after `migrate`.
- Empty phone / empty message / invalid phone produce validation errors.
- Missing Twilio credentials with `DEMO_MODE=false` produce a safe configuration error (no secret leakage).
- `DEMO_MODE=true` records a simulated queued/demo history entry and shows success feedback.
- Live Twilio send depends on valid account credentials and (for trial) a verified destination number — not exercised with invented credentials.

---

## Known limitations

- **Trial accounts:** Twilio often restricts sending to verified numbers only.
- **Submission ≠ delivery:** Success means accepted/queued by Twilio, not confirmed handset delivery.
- **Character encoding:** The ~160 hint assumes GSM-7; Unicode/emoji can use UCS-2 (~70 chars per segment).
- **Local SQLite only:** History is on the machine running the app; not a multi-user production store.
- **DEBUG / SECRET_KEY:** Defaults are for classroom demo — change before any real deployment.
- **No delivery webhooks:** Status callbacks / delivery receipts are out of scope for this lab.

---

## Security notes

- Credentials live only in environment variables (`.env`), loaded by `python-dotenv`.
- `.env` is listed in `.gitignore` and must not be committed.
- Forms use Django’s CSRF middleware/token.
- Error sanitization redacts SID/token strings before storing or showing provider errors.

---

## Email draft for submission

**To:** joshuatubo4@gmail.com  
**Subject:** Assignment_IT 120-1stSemSY26-27

```
Good day Sir,

Please find attached / linked our group submission for IT 120
(Integrative Programming and Technologies), 1st Sem SY 2026–2027.

Title: Django Web Application for Sending SMS (Twilio)

Group members:
- Member 1: [Full Name] — Django project setup, views, URLs, application logic
- Member 2: [Full Name] — UI, forms, validation, user feedback
- Member 3: [Full Name] — Twilio integration, testing, documentation, demonstration

Repository / drive link: [paste link here]

Thank you.

Respectfully,
[Group / section]
```

---

## License / academic use

Prepared for IT 120 laboratory/group assignment use. Replace member name placeholders before final submission.
