# Cyber Awareness Portal

## 1. Project overview

The Cyber Awareness Portal is a server-rendered web application for learning and practicing basic cybersecurity awareness. It provides:

- User registration, sign-in, profile management, and role-based access.
- Admin-managed learning categories, quizzes, awareness films, phishing scenarios, and news.
- Draft quiz generation with Groq, followed by admin review before publishing.
- Server-side quiz marking, attempt history, and PDF certificates for passing attempts.
- A certificate verification page and QR code embedded in each certificate.
- Safe, screenshot-only phishing-awareness exercises with clickable hotspots and scored feedback.
- Awareness-video viewing progress.
- Cybercrime articles retrieved from configured RSS feeds and summarized with Groq for admin review.
- Timed quiz attempts, paginated listings, and user/admin performance reporting.
- Clearly labeled fictional demo quizzes, phishing scenarios, and news for local demonstrations.
- Public quiz and news pages hide fictional demo records; administrators can opt into them with the demo-content filter.

There are exactly two account roles: `user` and `admin`. Public registration always creates a `user`; administrators are created through the Flask CLI.

The checked-in implementation is **Flask + SQLAlchemy + SQLite by default**, not Django/MySQL. The supplied project design document describes Django/MySQL as a proposed stack; this repository's actual dependencies and code determine the setup below. The UI is server-rendered HTML with local CSS and JavaScript; there is no separate frontend build.

## 2. Technology stack

- **Backend:** Python 3.10 or later; Flask 3.1.
- **Database/ORM:** Flask-SQLAlchemy and SQLAlchemy; SQLite is the default.
- **Schema migrations:** Flask-Migrate/Alembic.
- **Authentication and forms:** Flask-Login, Werkzeug password hashing, Flask-WTF CSRF protection, `email-validator`.
- **Frontend:** Jinja templates, HTML, CSS, and small browser-side JavaScript; no Node.js or Bootstrap dependency.
- **AI:** Groq through the official `groq` Python SDK. It drafts multiple-choice quizzes and summarizes fetched news; Groq is not used as a news source.
- **News retrieval:** Configurable RSS feeds parsed with `feedparser`.
- **Certificates and uploads:** ReportLab PDF output, `qrcode`, and Pillow image validation/normalization.
- **Production WSGI server:** Waitress.

Pinned Python dependencies are listed in [`requirements.txt`](requirements.txt).

## 3. Project folder structure

```text
.
├── app/
│   ├── accounts/          # User model and authentication/profile/admin-user routes
│   ├── certificates/      # Certificate model, PDF generation, verification/download
│   ├── learning/          # Categories, films/progress, cyber news/RSS routes
│   ├── main/              # Home, dashboards, categories, media serving
│   ├── phishing/          # Scenario/hotspot/attempt models and routes
│   ├── quizzes/           # Quiz models, generation, administration, attempts/results
│   ├── reports/           # Admin activity log model
│   ├── static/            # Portal CSS
│   ├── templates/         # Jinja HTML pages
│   ├── ai_client.py       # Reusable Groq client
│   ├── demo_data.py       # Idempotent fictional demonstration content
│   ├── config.py          # Environment-based configuration
│   ├── extensions.py      # Flask extension instances and SQLite FK setup
│   ├── uploads.py         # Safe screenshot/thumbnail validation and storage
│   └── utils.py           # Shared authorization, pagination, and validation helpers
├── media/                 # Runtime uploads and generated PDFs (not committed)
├── migrations/            # Alembic migration environment and schema revisions
├── tests/                 # Pytest behavior tests
├── .env.example           # Environment-variable template
├── requirements.txt
└── run.py                 # Flask application entry point
```

## 4. Prerequisites

- Python **3.10+** (the current project environment was validated with Python 3.14.4).
- Git, if cloning the source.
- A supported web browser.
- No separate database server is needed for the default SQLite configuration.
- No Node.js or frontend package manager is required.
- A Groq API key is optional for general portal use, but required for AI quiz generation and news summaries.

## 5. Installation and setup

### Windows PowerShell

If you have the repository URL:

```powershell
git clone <repository-url> CyberAwarenessPortal
Set-Location .\CyberAwarenessPortal
```

Or, from an already downloaded project directory:

```powershell
Set-Location <path-to-project>
```

Create and activate a virtual environment, then install dependencies:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

If PowerShell prevents environment activation, either allow local scripts for the current user or invoke commands directly as `.\.venv\Scripts\python.exe`.

Edit `.env` and set a unique secret key. Generate one with:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Paste the generated value into `SECRET_KEY`. Add `GROQ_API_KEY` if AI features are needed. Do not commit `.env`.

Initialize or update the database schema:

```powershell
flask --app run.py db upgrade
```

Create the first administrator interactively:

```powershell
flask --app run.py create-admin
```

The command prompts for a valid email address, full name, and a password of at least 12 characters. Public registration cannot create admins.

Optionally create fictional demo learning content after creating an administrator:

```powershell
flask --app run.py seed-demo
```

The command is idempotent and does not create user accounts or passwords. It adds seven categories, eight quizzes, five fictional phishing scenarios, and three clearly labeled fictional news items. Its two awareness-film records are inactive placeholders and must be replaced with real video links before publication. Uploaded demo screenshots are generated locally.

## 6. Environment variables

Copy `.env.example` to `.env`. The example contains placeholders only.

| Variable | Required | Purpose |
|---|---:|---|
| `SECRET_KEY` | Yes for deployment | Flask session and CSRF signing key; replace the example value with a long random secret. |
| `DEBUG` | No | Flask debug mode; defaults to `False`. Enable only for local development. |
| `SESSION_COOKIE_SECURE` | Production | Set `True` when the site is served over HTTPS. |
| `DATABASE_URL` | No | SQLAlchemy URL. Defaults to a SQLite file at the project root. `sqlite:///db.sqlite3` is resolved relative to the project root. |
| `GROQ_API_KEY` | For AI features | Private Groq API key; used only by the backend. |
| `GROQ_MODEL` | No | Groq model name; defaults to `openai/gpt-oss-20b`. |
| `GROQ_TIMEOUT_SECONDS` | No | AI request timeout from 1 to 120 seconds; defaults to `30`. |
| `RSS_FEEDS` | No | Comma-separated HTTPS RSS URLs. Defaults to The Hacker News, BleepingComputer, and KrebsOnSecurity feeds. |

Example:

```dotenv
SECRET_KEY=replace-with-a-long-random-string
DEBUG=False
SESSION_COOKIE_SECURE=False
DATABASE_URL=sqlite:///db.sqlite3
GROQ_API_KEY=
GROQ_MODEL=openai/gpt-oss-20b
GROQ_TIMEOUT_SECONDS=30
RSS_FEEDS=https://feeds.feedburner.com/TheHackersNews,https://www.bleepingcomputer.com/feed/,https://krebsonsecurity.com/feed/
```

The application does not currently require a News API key; it retrieves article metadata from RSS feeds. Groq only summarizes articles after retrieval. For a database other than SQLite, configure a compatible SQLAlchemy driver in the environment and provide its SQLAlchemy URL.

## 7. How to run

### Local development

Activate the virtual environment, apply the database migration if this is a fresh setup, and start the Flask server:

```powershell
flask --app run.py db upgrade
python run.py
```

The server listens on `http://127.0.0.1:5000` and serves both the backend and frontend pages. Open that URL in your browser; there is no separate frontend command or frontend development server.

Alternatively, start the same backend-and-frontend server with Flask's development command:

```powershell
flask --app run.py run --debug
```

Use the debug command only for local development. No separate frontend, background worker, or scheduled task is part of this project. News retrieval is initiated by an administrator from the News management page.

### Production

Set `DEBUG=False`, a strong `SECRET_KEY`, and `SESSION_COOKIE_SECURE=True` when HTTPS is terminated at the deployment boundary. Apply migrations and create the administrator as above. Start the WSGI app with Waitress:

```powershell
waitress-serve --listen=127.0.0.1:8000 --call app:create_app
```

Place a TLS-enabled reverse proxy in front of Waitress, restrict access to the host and database, back up SQLite and `media/`, and do not expose the Flask development server. SQLite is appropriate for a small single-instance demonstration; use a production database and its SQLAlchemy driver for concurrent/multi-instance deployments.

## 8. Database setup

SQLite is created automatically when the first migration is applied:

```powershell
flask --app run.py db upgrade
```

The initial migration creates the schema without deleting application data. Main tables include:

- `users`, `categories`, `admin_activity_logs`
- `quizzes` (including `is_demo`), `questions`, `question_options`, `quiz_attempts`, `attempt_answers`
- `certificates`
- `phishing_scenarios`, `phishing_hotspots`, `phishing_attempts`, `phishing_attempt_selections`
- `awareness_films`, `film_progress`, `login_attempts`
- `cyber_news` (including original and concise display titles, original article URL, AI summary, important points, safety advice, and `is_demo`)

Quiz attempts store their deadline and timeout state. `quizzes.is_demo` and `cyber_news.is_demo` distinguish fictional seed records; the latest migration also backfills older seeded quizzes using their dedicated seed description. Existing user and learning-history rows are retained. Create the first administrator with `flask --app run.py create-admin`. Demo data is optional; administrators can also create content in the admin pages. To create a migration after a model change:

```powershell
flask --app run.py db migrate -m "Describe the schema change"
flask --app run.py db upgrade
```

Review autogenerated migration files before applying them to a database with important data.

## 9. API integration setup

### Groq

1. Obtain a Groq API key from the Groq Console.
2. Set `GROQ_API_KEY` in the server's environment or `.env`.
3. Optionally set `GROQ_MODEL` and `GROQ_TIMEOUT_SECONDS`.
4. Use **Admin → Quizzes → Generate with Groq** for draft MCQs, or **Admin → News → Fetch RSS updates** for RSS ingestion and article summaries.
5. Review and edit generated content before publishing. AI-created quizzes and fetched articles begin as drafts.

The key is never sent to templates or browser JavaScript. Requests use a timeout, disable automatic retries, request strict JSON-schema output, and validate responses before database insertion/publication. Groq failures are reported in the admin UI; fetched articles with missing summaries remain unpublished drafts.

### RSS news

Set `RSS_FEEDS` to comma-separated trusted HTTPS RSS feed URLs. The admin manually fetches feeds; there is no scheduler. Duplicate original article URLs are skipped before calling Groq. Available RSS summary, description, and content fields are converted to plain text and provided as untrusted source material; entries with no article text are skipped. Groq provides a concise display title when useful, a plain-language summary, important points, category, and safety tips; the original publisher title and URL remain preserved. Each retrieved item remains a draft, including when Groq is unavailable; no synthetic news or replacement URL is created. Administrators review and publish valid summaries, and public cards link to the original article URL and source.

The Admin → Quizzes and Admin → News pages exclude demo records by default. Select **Include fictional demo content** to inspect them. Public pages and public detail routes exclude demo records regardless of publication status.

## 10. Application URLs

### Public and user pages

| Page | URL |
|---|---|
| Home | `/` |
| Registration / login | `/register`, `/login` |
| User dashboard | `/dashboard` |
| Admin reports | `/admin/reports` |
| Profile | `/profile` |
| Available quizzes / attempt history | `/quizzes`, `/quiz-history` |
| Take a quiz / view result | `/quizzes/<quiz_id>/attempt`, `/quiz-attempts/<attempt_id>` |
| Certificates / download / verification | `/certificates`, `/certificates/<certificate_id>/download`, `/certificates/verify` |
| Phishing practice / history | `/phishing`, `/phishing-history` |
| Awareness films | `/films`, `/films/<film_id>` |
| Cybercrime news | `/news`, `/news/<news_id>` |

### Admin pages

| Page | URL |
|---|---|
| Admin dashboard | `/dashboard` (admin role) |
| User management | `/admin/users` |
| Categories | `/admin/categories` |
| Quiz management / creation / AI drafts | `/admin/quizzes`, `/admin/quizzes/new`, `/admin/quizzes/generate` |
| Phishing scenario management | `/admin/phishing`, `/admin/phishing/new` |
| Film management | `/admin/films`, `/admin/films/new` |
| News retrieval and review | `/admin/news` |

The application currently exposes server-rendered form routes rather than a separate JSON REST API.

## 11. Troubleshooting

- **Database connection or migration errors:** Confirm `.env` and `DATABASE_URL`; for SQLite, ensure the project directory is writable. Run `flask --app run.py db upgrade`.
- **Missing dependencies:** Activate the correct virtual environment and run `python -m pip install -r requirements.txt`.
- **Port already in use:** Run the local Flask server on another port with `flask --app run.py run --port 5001`.
- **Admin cannot sign in:** Create the account with `flask --app run.py create-admin`; public sign-up intentionally only creates `user` accounts.
- **Groq says key missing or unavailable:** Set `GROQ_API_KEY` in `.env`, restart the server, and check the key, model availability, and account limits in the Groq Console.
- **AI response rejected:** Retry or reduce the generated quiz size. The service validates question count, option count, answer indices, and required fields before saving.
- **No RSS articles imported:** Check `RSS_FEEDS`, outbound HTTPS access, and feed availability. New items are drafts, not visible on public News until reviewed/published.
- **News summaries are blank:** Groq may be unconfigured, unavailable, or return invalid content. The article remains a draft for review.
- **Image upload rejected:** Use a valid PNG, JPG, or WEBP image under the 4 MB request limit and within the configured image-dimension limits.
- **Video does not play:** Use an HTTPS direct video URL supported by the browser or a YouTube/Vimeo player URL. External player completion is manually confirmed.
- **Secure-cookie behavior in local HTTP testing:** Keep `SESSION_COOKIE_SECURE=False` locally; set it to `True` only when using HTTPS.
- **Frontend/backend connection errors:** There is no separate frontend server; the Flask application serves the templates and static CSS itself.

## 12. Testing commands

Run the behavior tests:

```powershell
python -m pytest -q
```

The tests cover public registration role restrictions, login throttling, protected admin pages, quiz timing/evaluation and draft publication visibility, certificate download/verification, phishing hotspot scoring, mocked Groq quiz/news responses, RSS content extraction and URL deduplication, unpublished handling after summarization failures, public/demo separation, idempotent demo seeding, and a demo quiz attempt. External Groq and RSS network services are not contacted by the automated tests.

No separate linter or formatter is configured.

## 13. Production build and deployment

There is no frontend bundle or build command: HTML templates, local CSS, and JavaScript are served directly by Flask. Install dependencies, apply Alembic migrations, configure environment variables, create the admin account, and run the Waitress WSGI command shown above behind HTTPS.

Persist and back up the database and `media/` directory. Keep `.env` and generated PDFs/uploads private; the application only serves uploaded learning images publicly and provides certificate PDFs through an authenticated download route. Do not run with `DEBUG=True` in production.
