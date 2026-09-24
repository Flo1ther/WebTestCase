# TestFlow

TestFlow is a full-stack educational web system for managing software test cases. React communicates with a real Django REST API; Django persists users, projects, scenarios, executions and defects in PostgreSQL.

## Stack and architecture

- Frontend: React 18, Vite, TypeScript, React Router, Axios, CSS.
- Backend: Python, Django, Django REST Framework, SimpleJWT, CORS headers.
- Database: PostgreSQL 16.

`React SPA -> Axios/JWT -> Django REST API -> Django ORM -> PostgreSQL`

The backend is split into `accounts`, `projects`, `test_cases`, `executions`, `defects`, and `reports`. The frontend separates layout, shared UI, auth context, pages and API service.

## Local startup

Prerequisites: Python 3.11+ with `pip`, Node.js 20+, and a running PostgreSQL server.

```powershell
cd D:\WTC\testflow
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Create a PostgreSQL database and role before migration (or set equivalent credentials in `DATABASE_URL`):

```sql
CREATE USER testflow WITH PASSWORD 'testflow';
CREATE DATABASE testflow OWNER testflow;
```

In a second terminal:

```powershell
cd D:\WTC\testflow\frontend
Copy-Item .env.example .env
npm install
npm run dev
```

Open `http://localhost:5173`. Backend API is at `http://localhost:8000/api/`.

## Docker Compose

With Docker Desktop installed, `docker compose up --build` starts PostgreSQL, backend and frontend with the same URLs. Docker is optional; local startup above remains supported.

## Demo accounts

All demo accounts use password `DemoPass123!`.

| Role | Login |
| --- | --- |
| Administrator | `admin@example.com` (or `admin`) |
| Test manager | `manager@example.com` (or `manager`) |
| Tester | `tester@example.com` (or `tester`) |

## Roles

- Administrator: user administration, blocking, roles, project deletion, all reports.
- Manager: projects, test case CRUD and assignment, all executions, defects and reports.
- Tester: assigned cases only, new executions, related defect reports and personal statistics.

Role checks are enforced in DRF queryset/permission logic as well as in frontend navigation.

## Key endpoints

- `POST /api/auth/register/`, `POST /api/auth/login/`, `POST /api/auth/refresh/`, `GET /api/auth/me/`
- `GET|POST /api/projects/`, `GET|PUT|DELETE /api/projects/{id}/`
- `GET|POST /api/test-cases/`, `GET|PUT|DELETE /api/test-cases/{id}/`
- `GET|POST /api/executions/`
- `GET|POST /api/defects/`, `PUT /api/defects/{id}/`
- `GET /api/dashboard/`, `GET /api/reports/`, `GET|POST|PATCH /api/users/`

List endpoints support DRF pagination plus search/filter parameters such as `page`, `search`, `status`, `priority`, `project`, and `assigned_to` where relevant.

## Main user flow

Sign in as manager -> create a project/test case -> assign the tester -> sign in as tester -> open the assigned case -> Execute test -> choose Passed/Failed/Blocked/Not Run -> review immutable execution history and reports.
