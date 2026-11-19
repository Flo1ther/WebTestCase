# WebTestCase

WebTestCase is a project-centred QA management system for small development and testing teams. It is a learning-scale analogue of TestRail, Xray and Zephyr: every working record belongs to one software project, starting from a requirement and ending with an execution, defect and quality report.

The application is not a static mock-up. React communicates with Django REST Framework, Django validates roles and business rules, and PostgreSQL stores the complete history.

## Core workflow

```text
Project
  -> project description and AI context
  -> requirements
  -> manual test cases and optional API tests
  -> test suites and test runs
  -> executions with PASS / FAIL / BLOCKED / NOT RUN
  -> defects with actual evidence
  -> project analytics, requirement coverage and report
```

A Requirement describes expected product behaviour. A Test Case describes how a person verifies that requirement. An API Test describes an HTTP check for the same requirement. An Execution stores the actual outcome and never overwrites earlier history. A Defect is linked to the project, test case and, when known, its requirement and test run.

## Architecture

```text
React + Vite browser client
        |
same-origin /api with session cookie and CSRF protection
        |
Django REST Framework -> serializers -> business rules -> Django ORM
        |
PostgreSQL
```

Main applications:

```text
apps/projects       Project workspace, context, per-project analytics and reports
apps/requirements   Business requirements and coverage links
apps/test_cases     Manual test cases, steps and suites
apps/executions     Test runs, manual execution history and API tests
apps/defects        Defects with reproducible QA evidence
apps/ai_assistant   Optional Ollama/external LLM plus deterministic QA checks
apps/analytics      Global cross-project analytics
apps/reports        Global summary reports
apps/security       Authentication, OIDC, 2FA, rate limits and audit security
apps/audit          Business action audit log
frontend            React/Vite user interface
```

## Project workspace model

`Project` is the root entity. It contains name, description, status and `ai_context`. The context is a short domain description for the AI assistant: users, vocabulary, constraints, acceptance rules or supported integrations.

Manual test cases have an optional primary `requirement` field. Existing many-to-many requirement links are retained for compatibility, but the primary relation is used when a manager explicitly creates a test for one requirement. API tests can also be attached to a requirement. The coverage calculation counts a requirement as covered when it has at least one manual test or API test.

New project endpoints:

| Endpoint | Purpose |
|---|---|
| `GET /api/projects/{id}/workspace/` | Project overview, metrics, requirement coverage, recent executions and defects |
| `GET /api/projects/{id}/analytics/` | Project-only quality metrics, priority and defect distributions |
| `GET /api/projects/{id}/reports/` | Backend-generated quality report payload |
| `GET /api/projects/{id}/ai/coverage-summary/` | Deterministic readable coverage summary, available even without an LLM |

The existing resource endpoints remain available during the frontend migration and accept `?project=<id>` filtering: `requirements/`, `test-cases/`, `test-runs/`, `executions/`, `defects/` and `api-tests/`.

## Roles

- **ADMIN** manages users and has full access to every project.
- **MANAGER** creates projects, requirements, tests, runs, API tests and reports.
- **TESTER** sees assigned cases, records actual results and reports defects for assigned cases.

Role checks are made by Django. A user cannot link a requirement from Project A to a test case or API test from Project B. Executions and defects inherit their project server-side from the selected test case.

## AI QA Assistant

The assistant is a project tool, not an autonomous test runner.

1. The manager chooses a Project and optional Requirement.
2. The backend supplies the project AI context, selected requirement and safe relevant data to the configured provider.
3. The assistant returns a draft test case or review findings.
4. The manager edits, accepts or rejects the draft. No test case is created automatically.

AI can generate a manual test-case draft, review a test case, review a requirement and summarise project coverage. It does not open external websites, click UI elements or decide real PASS/FAIL. PASS/FAIL is set by a tester or by the API runner after an actual request.

`AI_PROVIDER=local` uses transparent deterministic structural checks. `AI_PROVIDER=ollama` calls a local Ollama model over `localhost`. External mode requires `AI_API_KEY`; keys never reach React.

## API testing

API testing is optional for each project and requirement. A manager enters HTTP method, local URL, headers, JSON payload, expected status and JSON assertions. The backend runner performs the request and stores actual status, duration, response preview and assertion results.

For safety, the runner accepts only `http://localhost` and `http://127.0.0.1`, strips Authorization/Cookie headers and uses a timeout. The local Demo Store API intentionally contains one known defect: an invalid payment token returns `201` instead of expected `400`. This provides a reproducible real FAIL for a demo.

## GitHub Actions integration

WebTestCase does not execute arbitrary repository code itself. GitHub Actions runs the repository's own tests in an isolated runner; after the job ends, the workflow sends a signed result to WebTestCase. The backend then maps each `automation_key` to a test case in the selected project, creates a completed **Test Run** and immutable **execution history** records. Thus the chain is traceable:

```text
Git push -> GitHub Actions runs pytest / Playwright / API tests
         -> signed HTTPS callback
         -> GitHub workflow run + Test Run + TestExecution
         -> project analytics, reports and requirement coverage
```

### Local presentation without GitHub

1. Open a project → **GitHub CI**.
2. On a test case, set an optional unique **Ключ автоматизації**, for example `TC-AUTH-LOGIN`.
3. In **GitHub CI**, enter any repository name in the `owner/repository` format and click **Прив’язати репозиторій**.
4. Select that test case, choose `PASSED`, `FAILED` or `BLOCKED`, then click **Симулювати CI-результат**.

This is explicitly shown in the interface as a local simulation, but it calls the same backend result mapper as the real callback. It creates a Test Run and TestExecution; it is not a manually prefilled dashboard value.

### Real GitHub Actions connection

1. Generate a long random value and add it to the ignored backend `.env` file:

   ```env
   GITHUB_WEBHOOK_SECRET=your-long-random-secret
   PUBLIC_API_URL=https://your-public-https-domain
   ```

   Restart Django. `PUBLIC_API_URL` must be publicly reachable by GitHub; `localhost` works only for the local simulation. For a presentation, a temporary HTTPS tunnel such as Cloudflare Tunnel may be used.
2. In WebTestCase, create the project integration with the exact GitHub repository name, for example `student/shop-api`.
3. Copy [webtestcase-ci.yml](docs/github-actions/webtestcase-ci.yml) into the target repository as `.github/workflows/webtestcase-ci.yml`.
4. In GitHub repository **Settings → Secrets and variables → Actions**, add:

   ```text
   WEBTESTCASE_CALLBACK_URL=https://your-public-https-domain/api/integrations/github/callback/
   WEBTESTCASE_WEBHOOK_SECRET=the-same-value-as-GITHUB_WEBHOOK_SECRET
   ```

5. Make the project tests produce an optional `webtestcase-results.json` file:

   ```json
   {
     "tests": [
       {
         "automation_key": "TC-AUTH-LOGIN",
         "status": "PASSED",
         "actual_result": "pytest: test_login_valid_credentials passed",
         "comment": "Chrome 128, GitHub Actions"
       }
     ]
   }
   ```

The callback verifies `X-Hub-Signature-256` with HMAC-SHA256 before accepting data. An invalid signature receives `401`; retries of the same `run_id` cannot duplicate executions.

## Laboratory 12: refactoring with design patterns

Two patterns are integrated into real WebTestCase workflows rather than added as isolated examples.

- **State** controls the persisted lifecycle of a test run: `DRAFT → ACTIVE → COMPLETED`. A manager uses `POST /api/test-runs/{id}/start/` and `POST /api/test-runs/{id}/complete/`; direct status PATCH is rejected. An execution linked to a run is accepted only while that run is active.
- **Factory Method** chooses a backend project report without coupling the view to a concrete report class. `GET /api/projects/{id}/reports/?type=quality`, `traceability` or `execution` returns a quality summary, coverage matrix or execution-progress report respectively. The default remains `quality` for compatibility.

The analysis, diagrams, changed components and test checklist are in `docs/LAB_12.md`.

## Prerequisites

- Python 3.12+
- Node.js 22.12+ or 24+
- PostgreSQL 16+ or Docker Desktop

## Local Windows launch

```powershell
cd D:\WTC\testflow
.\scripts\start-local.ps1
```

Open `http://localhost:5173`. Backend health endpoint: `http://localhost:8000/api/health/`. The script applies migrations and starts Django, Vite and local Mailpit. Stop background web processes with:

```powershell
.\scripts\stop-local.ps1
```

### Send laboratory emails to a real Gmail inbox (optional)

By default the local project delivers activation and password-reset emails to Mailpit at `http://localhost:18025`. To demonstrate actual delivery to a personal Gmail inbox, first enable two-step verification for that Gmail account and create a **Gmail App Password**. Do not use or share the normal Google password. Then run this locally; it asks for the secret securely and saves it only in the ignored `.env` file:

```powershell
.\scripts\configure-gmail-smtp.ps1
.\scripts\restart-backend.ps1
```

Register a new test address and check its real inbox. To return to the local demonstration mail server, set `EMAIL_HOST=127.0.0.1`, `EMAIL_PORT=11025`, `EMAIL_USE_TLS=false`, clear `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` in `.env`, then restart the backend.

### Enable real Google sign-in (OpenID Connect)

Google sign-in is separate from Gmail SMTP. Create a **Web application** OAuth client in Google Cloud, complete the OAuth branding/consent screen and add your Google account as a test user if the app is in testing mode. Add both exact authorized redirect URIs to the OAuth client:

```text
http://localhost:5173/api/auth/oidc/callback/
http://127.0.0.1:5173/api/auth/oidc/callback/
```

Then save the Client ID and Client Secret locally without placing them in the repository:

```powershell
.\scripts\configure-google-oidc.ps1
.\scripts\restart-backend.ps1
```

Reload the login page. The Google button becomes active. The redirect URI must match Google Cloud exactly, including protocol, host, port, path and final slash.

For a clean local environment:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.venv\Scripts\python.exe scripts\bootstrap.py
# Set a valid PostgreSQL DATABASE_URL in .env.
.venv\Scripts\python.exe manage.py migrate
cd frontend
npm ci
cd ..
.\scripts\start-local.ps1
```

## Docker Compose

```powershell
cd D:\WTC\testflow
.venv\Scripts\python.exe scripts\bootstrap.py
docker compose up --build -d
docker compose logs --tail 50 backend
```

Compose starts PostgreSQL, Django/gunicorn, React/nginx and Mailpit. `DEMO_SEED_ON_START=true` is the default in `.env.example`; it idempotently creates the learning demo data after migrations. Set it to `false` for an empty database.

```powershell
docker compose down
```

`docker compose down` preserves `postgres_data`. Do not use `-v` unless deleting the database is intentional.

## Environment variables

Copy from `.env.example` or run `scripts/bootstrap.py`; never commit `.env`.

| Variable | Meaning |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | Django secret |
| `DEBUG` | Local debug mode only |
| `ALLOWED_HOSTS` | Allowed backend hostnames |
| `CORS_ALLOWED_ORIGINS` | Development frontend origins |
| `DEMO_SEED_ON_START` | Docker demo-data seed switch |
| `AI_PROVIDER` | `local`, `ollama` or external provider name |
| `AI_MODEL` | Selected LLM model |
| `OLLAMA_API_URL` | Local Ollama chat endpoint |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Google OIDC settings |

## Demo data and accounts

```powershell
.venv\Scripts\python.exe manage.py seed_demo
.venv\Scripts\python.exe manage.py seed_quality_demo
.venv\Scripts\python.exe manage.py seed_ai_copilot_demo
```

| Role | Login | Password |
|---|---|---|
| Administrator | `admin@example.com` | `DemoPass123!` |
| Manager | `manager@example.com` | `DemoPass123!` |
| Tester | `tester@example.com` | `DemoPass123!` |

`seed_demo` creates projects, requirements and manual cases. `seed_quality_demo` creates the project-centred API checkout scenario: `Demo Store API -> REQ-CHECKOUT-01 -> manual/API test -> Test Run`. `seed_ai_copilot_demo` creates the deliberately inconsistent registration case for the AI review demonstration.

## Verification

```powershell
.venv\Scripts\python.exe manage.py check
.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.venv\Scripts\python.exe -m pytest -q
cd frontend
npm run build
cd ..
docker compose config --quiet
```

The backend suite includes project-isolation, requirement coverage and direct project inheritance tests. The current verified result is **78 passed**.

## Security notes

Authentication uses HttpOnly session cookies and CSRF protection. Passwords are hashed with Argon2id. For the local laboratory workflow, `EMAIL_VERIFICATION_REQUIRED=true` makes a new account activate only through its one-time Mailpit email link. The project also includes login rate limiting, optional TOTP and Google OIDC configuration. Production requires HTTPS, real SMTP/CAPTCHA credentials, production secrets and a configured Google OAuth client.

For deeper documentation see [project workflow](docs/PROJECT_CENTRIC_WORKFLOW_UK.md), [AI workflow](docs/AI_WORKFLOW_UK.md), [Demo API](docs/DEMO_API.md), and [security integration](docs/SECURITY_INTEGRATION_UK.md).
