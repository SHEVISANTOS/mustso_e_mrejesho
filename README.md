# MUST e-Mrejesho

**Student Government Accountability Monitoring and Feedback System** for
Mbeya University of Science and Technology (MUST), inspired by the national
[e-Mrejesho](https://emrejesho.gov.go.tz) platform.

Built to satisfy the project's four specific objectives:

1. **Real-time dashboards** for resolution tracking — live-updating stat cards, a status
   chart, and a feedback table that refresh automatically without a page reload.
2. **Role-based access control** — Student, Representative, Admin, each scoped to exactly
   the data they should see.
3. **Automated notifications** — in-app notification bell + email, fired on submission,
   escalation, and resolution.
4. **Automated testing** — 19 Django test cases covering all of the above (see
   `MUST_eMrejesho_Testing_Report.docx` for the full test report).

Registered students submit **Malalamiko** (Complaints), **Mapendekezo** (Suggestions),
**Maulizo** (Inquiries), or **Pongezi** (Compliments), routed to the relevant department
and escalated to Admin if unresolved.

## Roles & escalation chain

```
Student  --submits-->  Representative (per department)  --escalate-->  Admin (final)
```

- **Student**: submits feedback, tracks its status, sees only their own items.
- **Representative**: first responder for their department. Comments, resolves, or escalates.
- **Admin**: sees everything university-wide; final escalation point; receives every
  escalation notification.

Every action (comment, escalation, resolution, closure) is logged in a full audit trail
(`FeedbackUpdate`) attached to each feedback item, visible on its detail page.

## Project structure

```
accounts/       - custom User model (role-based), registration & login
departments/    - Department model (name, code)
feedback/       - Feedback + FeedbackUpdate models, live dashboard, escalation logic
notifications/  - Notification model, in-app bell, email dispatch
templates/      - Bootstrap 5 templates (MUST green/gold theme)
```

## Setup

```bash
python -m venv venv
source venv/bin/activate        # venv\Scripts\activate on Windows
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser   # create your first Admin
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` — it redirects to the login page.

## Setting up departments & staff

1. Log in to `/admin/` with your superuser account.
2. Under **Departments**, create entries (e.g. ICT, Hostels/Housing, Academics, Finance,
   or a student-government organ like a Faculty Student Council).
3. Under **Users**, create accounts for Representatives, assigning each to a Department
   with `role = REPRESENTATIVE`. Create Admin accounts with `role = ADMIN`.
4. Students self-register at `/accounts/register/` (always creates a Student account).

## Admin panels

There are **two separate admin panels**, for two different purposes:

### 1. Django Admin (`/admin/`) — branded with django-jazzmin
For raw data management: bulk-editing Users, Departments, Feedback, and Notifications,
with search, filters, and inline audit trails. Branded in MUST green/gold via
`JAZZMIN_SETTINGS` / `JAZZMIN_UI_TWEAKS` in `settings.py` — no template overrides needed.
Log in with a superuser account (`python manage.py createsuperuser`).

### 2. In-app Admin Panel (`/adminpanel/`) — for day-to-day use by Admin-role users
This is what your Admin-role users actually work in day to day; it sits behind the
`admin_required` decorator (`adminpanel/decorators.py`), which checks `role == ADMIN` and
returns 403 for anyone else. Reachable via the "Admin Panel" button in the navbar
(only visible to Admins).

- **Analytics dashboard** (`/adminpanel/`) — KPIs (total cases, resolution rate, average
  resolution time, cases at Admin level, active departments/representatives) plus four
  live charts (cases by department, by category, by status, and a 30-day submission
  trend) and a department performance table (total vs. resolved cases per department).
- **Department management** (`/adminpanel/departments/`) — create, edit, and
  activate/deactivate departments without touching `/admin/`.
- **Staff accounts** (`/adminpanel/users/`) — the *only* place Representative and Admin
  accounts get created (`adminpanel/forms.py:RepresentativeForm`). Self-registration at
  `/accounts/register/` always forces `role = STUDENT`, so elevated roles can only be
  provisioned here or via `/admin/` by someone who already holds Admin access.

## Notifications & email

By default, `EMAIL_BACKEND` is set to Django's console backend — emails print to the
terminal instead of actually sending, so you can see them working with zero setup.

### Setting up real email for your live demo

You need one real email account to send from. **Gmail is the fastest option** if you
don't already have a university SMTP account:

1. Use (or create) a Gmail account, e.g. `mustemrejesho@gmail.com`.
2. Turn on 2-Step Verification: [myaccount.google.com/security](https://myaccount.google.com/security).
3. Create an **App Password**: [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
   → choose "Mail" → generate. Copy the 16-character password (you won't see it again).
   *(Your normal Gmail password will NOT work here — Google blocks it for security.)*
4. Set these environment variables before running the server:
   ```bash
   export EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   export EMAIL_HOST=smtp.gmail.com
   export EMAIL_PORT=587
   export EMAIL_USE_TLS=True
   export EMAIL_HOST_USER=mustemrejesho@gmail.com
   export EMAIL_HOST_PASSWORD=the16charapppassword
   export DEFAULT_FROM_EMAIL="MUST e-Mrejesho <mustemrejesho@gmail.com>"
   ```
   On Windows (PowerShell), use `$env:EMAIL_BACKEND = "..."` instead of `export`.
5. Restart `python manage.py runserver` after setting these (env vars are only read at
   startup).
6. **Test it before your demo, not during it**:
   ```bash
   python manage.py shell -c "
   from django.core.mail import send_mail
   send_mail('Test', 'It works!', None, ['your_real_inbox@gmail.com'])
   print('sent')
   "
   ```
   Check your inbox (and spam folder — a fresh Gmail app password sometimes lands there
   for the first email). If this works, the whole system's emails will work.

**If your university has its own mail server** (e.g. `mail.must.ac.tz`), ask ICT for the
SMTP host/port/username/password and use those instead of Gmail's — same environment
variables, different values.

**For the demo itself:** register two real email addresses you control as test accounts
(one Student, one Representative) so you can show the examiner an actual inbox receiving
a notification live, rather than just describing it.

## Real-time updates (WebSocket push)

The live dashboard and notification bell use **Django Channels** for true push updates —
not polling. When any feedback event happens (submission, comment, escalation,
resolution, closure), the server pushes an update over WebSocket to every connected
client in under a second:

- `/ws/dashboard/` — every logged-in user's open dashboard gets a "something changed"
  signal and instantly re-fetches its (role-scoped) data from `/feedback/data/`.
- `/ws/notifications/` — the specific recipient of a notification gets their unread
  count pushed to them directly, updating the bell badge immediately.

A slow 30-second poll still runs in the background as a safety net in case a socket
drops, but under normal conditions you should see updates appear instantly — open two
browser windows (e.g. a Student and a Representative) side by side to demo this live.

**How this is wired:**
- `channels` + `daphne` are installed and registered in `INSTALLED_APPS` (`daphne` must
  be listed *first* — this is what makes plain `python manage.py runserver` automatically
  serve both HTTP and WebSocket traffic, no separate command needed).
- `must_mrejesho/asgi.py` routes `/ws/...` paths to Channels consumers, everything else
  to normal Django.
- `notifications/consumers.py` defines the two consumers; `notifications/services.py`
  broadcasts to them every time a `Notification` is created.
- `CHANNEL_LAYERS` uses `InMemoryChannelLayer` — perfect for a single-process demo
  (`runserver`), but **it only works within one process**. If you ever deploy behind
  multiple Gunicorn/Daphne workers, switch to `channels_redis` instead:
  ```bash
  pip install channels_redis
  ```
  ```python
  CHANNEL_LAYERS = {
      'default': {
          'BACKEND': 'channels_redis.core.RedisChannelLayer',
          'CONFIG': {"hosts": [('127.0.0.1', 6379)]},
      }
  }
  ```

**Important for the demo:** `ALLOWED_HOSTS` must include whatever host/IP you're browsing
from — WebSocket origin validation checks it even in `DEBUG` mode (regular HTTP doesn't
enforce this as strictly, which is easy to overlook). It's already set to
`['localhost', '127.0.0.1']`. If you demo from another machine/IP on the same network
(e.g. presenting from a projector), add that IP too before you start:
```python
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '192.168.1.50']
```

## Running the tests

```bash
python manage.py test
```

All 19 tests should pass. See `MUST_eMrejesho_Testing_Report.docx` for the full
objective-by-objective test report, formatted for inclusion in your dissertation.

## Key workflow notes

- Feedback gets a public tracking number automatically, e.g. `MREJ-2026-705902`.
- A Representative only sees items at **their** department at escalation level 1.
  Once escalated, it disappears from their inbox and appears for every Admin.
- `Feedback.escalate(actor, reason)` and `Feedback.mark_resolved(actor, message)` are the
  two model methods driving the workflow — call these from anywhere (e.g. a management
  command for SLA auto-escalation) rather than duplicating the logic. Both automatically
  fire the appropriate notifications.

## Suggested next steps

- Add a scheduled job (Celery/cron) to auto-escalate cases that pass their `due_at` SLA deadline.
- Add a public tracking-number lookup page for students who forget to log in.
- Add SMS notifications (e.g. Africa's Talking) alongside email for students without
  reliable data access.
- For multi-worker production deployment, swap `InMemoryChannelLayer` for
  `channels_redis` (see above) so WebSocket broadcasts reach clients connected to a
  different worker process.

