# Django Web Application for Sending SMS (TextBee)

**Course:** IT 120 – Integrative Programming and Technologies  
**Semester:** 1st Sem SY 2026–2027  
**Title:** Django Web Application for Sending SMS  
**App name:** PulseSMS  
**SMS provider:** TextBee (assignment allows a provider such as Twilio)

A Django web app that lets a user enter a recipient phone number and message, validates input (including E.164 format), and **sends SMS through the real TextBee gateway API by default**. TextBee delivers messages via your registered Android phone’s SIM. An optional demo mode exists for offline development only and does not replace actual SMS functionality.

> **Important:** A `200` from TextBee means the message was **queued for your device**, not that the recipient’s handset already received it.

---

## Group members and responsibilities

| Member | Responsibilities |
|--------|------------------|
| **Irvin O. Demonguitan** | Django project setup, views, URLs, application logic, SMS provider integration |
| **Angelbert M. Sisora** | UI, forms, validation, user feedback, testing, documentation, demonstration |

---

## Main features

1. SMS compose form (CSRF-protected POST)
2. E.164 phone + message validation
3. **Actual TextBee send (default)** via `POST /gateway/send-sms`
4. Optional `DEMO_MODE` simulation (never silent fallback)
5. History with status, batch ID, errors, demo/actual flag
6. Character counter (~160 GSM-7 hint)
7. Safe errors (no API key leakage)

---

## Technologies

Python 3, Django 5.2, TextBee REST API, `requests`, python-dotenv, SQLite, Bootstrap 5 + custom CSS

---

## Installation

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Configure `.env`:

```env
TEXTBEE_BASE_URL=https://api.textbee.dev/api/v1
TEXTBEE_API_KEY=your_textbee_api_key
TEXTBEE_DEVICE_ID=your_device_id
SECRET_KEY=django-insecure-change-me
DEBUG=True
DEMO_MODE=false
```

```powershell
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000/

---

## TextBee setup

1. Create a TextBee account and verify email: https://textbee.dev/
2. Install the TextBee Android app and register your phone (keep it online)
3. Create an API key in the dashboard
4. Copy Device ID from Devices (recommended)
5. Put values only in `.env` — never commit secrets
6. Restart `runserver` after `.env` changes

---

## Actual vs demo mode

| Setting | Result |
|---------|--------|
| `DEMO_MODE=false` + API key | Live TextBee send; history **Actual** / usually **Queued** + `smsBatchId` |
| `DEMO_MODE=false` + missing key | Configuration error; **Failed**; no simulation |
| `DEMO_MODE=true` | Offline simulation only |

---

## Testing

```bash
python manage.py test sms_app
```

Automated tests mock TextBee (no real SMS).

Manual: valid send with phone online; empty/invalid inputs; missing credentials; character counter.

---

## Security

- Secrets only in `.env` (gitignored)
- CSRF enabled
- API keys redacted from user-facing errors
- Rotate any key that was pasted into chat

---

## Known limitations

- TextBee requires an online registered Android device
- API acceptance ≠ handset delivery
- Local SQLite history only
