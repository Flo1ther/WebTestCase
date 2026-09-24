# Laboratory work 6-7: TestFlow frontend

## Goal

Develop a responsive frontend for a test-case management system and connect it to a real REST backend with persistent PostgreSQL storage.

## User scenarios

1. A manager signs in, creates a project and a test case with ordered steps, then assigns it to a tester.
2. A tester sees only assigned cases, records an actual result and status, and reports a defect when needed.
3. An administrator manages users and roles, blocks access, and reviews global indicators.

## Navigation map

`Login -> Dashboard -> Projects -> Project details -> Test cases -> Details -> Execute test`.

The dashboard also leads to Executions, Defects, Reports and Profile. The administrator additionally receives Users. Logout returns to Login. Unauthorized routes redirect to Login; disallowed role actions show Access denied.

## Interface decomposition

`AuthProvider + Router -> Guard -> Layout -> Sidebar / top header / page content`.

Reusable components include Loader, Empty state, status Badge, Notice, Modal and Pagination. Page modules implement the dashboard, authentication, projects, test cases, executions, defects, reports, profile and user administration.

## Main screens

- Dashboard: totals, progress bar, recent cases and executions.
- Projects: search, project cards and project-specific scenario list.
- Test cases: filtered paginated list; dynamic step editor for create/edit.
- Test case detail: scenario, steps, metadata, execution history, related defects and action dialogs.
- Executions, Defects and Reports: audit records, issue status workflow and backend-provided indicators.

## REST and data interaction

Axios reads `VITE_API_URL`, sends access JWT in the Authorization header, and refreshes a token after a 401 response. Django REST Framework authenticates JWT, validates serializers, applies permissions/queryset scopes, and persists models through Django ORM to PostgreSQL. API errors and network errors become visible notices; loading and empty states are rendered in each data view.

## Responsive design

Desktop uses a sticky sidebar and spacious content grid. At 900px it becomes an overlay navigation opened by a hamburger button. At 600px grids collapse, filters wrap, forms become a single column, and table rows turn into labelled mobile records. CSS Grid, Flexbox and media queries control the adaptation.

## Validation and usability

HTML constraints cover required fields, email and password length. React verifies matching passwords and complete test steps. DRF serializers check password validity, mandatory steps, assignment only to testers and execution ownership. Confirm dialogs protect deletions; buttons, badges, loader, notices, empty states and modal cancellation keep the system state visible and controllable.

## Design decisions and conclusion

The project deliberately uses a compact dependency set: React Router and Axios on the client; DRF, SimpleJWT and django-filter on the server. Responsibilities are separated by domain Django apps and reusable UI components. The result demonstrates real asynchronous CRUD, role-based access control, responsive layout and the React -> Django REST API -> PostgreSQL workflow required by laboratory work 6-7.
