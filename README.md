# Leave & Expense Automation

Policy-aware leave and expense workflow automation with auditable approvals, reproducible synthetic data, and an AI policy assistant.

## Planned stack
- Frontend: React, TypeScript, Vite
- Backend: Python, FastAPI, SQLAlchemy, Alembic
- Database: PostgreSQL
- AI: LLM API with retrieval-augmented generation (RAG)
- Tests: pytest, HTTPX

## Project status
This archive creates the planned folder structure and starter documentation. Application modules are placeholders and still need implementation.

## Planned data volumes
- 400 employees
- 6 leave policies
- 800 leave requests
- 1,000 expense claims with 1–10 lines each
- Fixed generator seed: `20261022`

## Initial setup (after implementation)
1. Configure environment variables using the `.env.example` files.
2. Start PostgreSQL.
3. Install backend dependencies and apply migrations.
4. Install frontend dependencies.
5. Generate and validate synthetic data.
6. Start the API and frontend.

See `docs/architecture.md` and `docs/business-rules.md` for design notes.


## PostgreSQL model implementation

The SQLAlchemy 2.0 model layer is implemented under `backend/app/db/models/` and includes all 11 required entities plus `AuditEvent`. Database setup is in `backend/app/db/base.py` and `backend/app/db/session.py`; Alembic's environment imports the full model metadata.

### Apply database migrations

Run from `backend/`:

```bash
python -m pip install -r requirements.txt
# Copy the root .env.example to .env and confirm DATABASE_URL
alembic revision --autogenerate -m "create leave and expense models"
alembic upgrade head
```

The autogenerate command creates a migration file under `backend/alembic/versions/`; inspect it before running `upgrade head`. See `backend/app/db/models/README.md` for table descriptions and business-rule limitations.


========================================================================================================
# Leave & Expense Automation

A full-stack workflow automation project for employee leave and expense management. The backend is being built with Python, FastAPI, SQLAlchemy, Alembic, and PostgreSQL. A React/Vite frontend is part of the planned stack.

**Project status:** Initial database schema and FastAPI health check are working. Employee API implementation is in progress; route registration and database operations still need to be verified.

## Table of Contents

- [Project Overview](#project-overview)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Database Models](#database-models)
- [Environment Configuration](#environment-configuration)
- [Setup and Run](#setup-and-run)
- [Current API](#current-api)
- [Employee API](#employee-api)
- [Verification So Far](#verification-so-far)
- [Next Steps](#next-steps)

## Project Overview

The project is intended to automate employee leave and expense workflows, including:

- Employee records and reporting relationships
- Leave policies, requests, and balances
- Expense policies, claims, and line items
- Cost centers and budget tracking
- Approval rules and approval steps
- Reimbursements
- Audit events
- Planned analytics and AI-assisted workflow support

The database models have been created, but the complete workflow functionality is not yet implemented.

## Technology Stack

### Backend

- Python
- FastAPI
- Pydantic Settings
- SQLAlchemy
- Alembic
- PostgreSQL 16
- Psycopg PostgreSQL driver
- Uvicorn

### Frontend

- React
- Vite

The frontend is part of the planned project stack. Its implementation and integration are not yet verified.

## Project Structure

Current backend structure:

```text
leave-expense-automation/
├── backend/
│   ├── alembic/
│   │   └── versions/
│   ├── alembic.ini
│   ├── app/
│   │   ├── ai/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── endpoints/
│   │   │       │   ├── ai.py
│   │   │       │   ├── analytics.py
│   │   │       │   ├── approvals.py
│   │   │       │   ├── audit.py
│   │   │       │   ├── employees.py
│   │   │       │   ├── expenses.py
│   │   │       │   ├── leave.py
│   │   │       │   └── reimbursements.py
│   │   │       └── router.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── logging.py
│   │   │   └── security.py
│   │   ├── db/
│   │   │   ├── base.py
│   │   │   ├── session.py
│   │   │   └── models/
│   │   │       ├── __init__.py
│   │   │       └── models.py
│   │   ├── repositories/
│   │   ├── rules/
│   │   ├── schemas/
│   │   │   └── employees.py
│   │   ├── services/
│   │   ├── utils/
│   │   ├── workflows/
│   │   ├── main.py
│   │   └── __init__.py
│   ├── requirements.txt
│   └── tests/
└── README.md
```

Some endpoint files and folders are scaffolding or TODOs. Their presence does not mean their functionality is complete.

## Database Models

The SQLAlchemy model module defines 12 application models:

| Model | Purpose |
|---|---|
| `Employee` | Employee identity, employment details, manager, and cost center |
| `LeavePolicy` | Leave entitlements and policy rules |
| `LeaveBalance` | Employee leave balance by policy and year |
| `LeaveRequest` | Requested leave dates, duration, status, and decision details |
| `ExpensePolicy` | Expense limits, receipt requirements, and policy rules |
| `CostCenter` | Cost center ownership, currency, and budget information |
| `ExpenseClaim` | Expense claim details, amount, receipt metadata, and status |
| `ExpenseLine` | Individual line items belonging to an expense claim |
| `ApprovalRule` | Rules used to determine approval routing |
| `ApprovalStep` | Individual approval steps for leave or expense requests |
| `Reimbursement` | Reimbursement amount, status, and payment reference |
| `AuditEvent` | Append-oriented event history for application actions |

The initial Alembic migration has been applied to the `leave_expense` PostgreSQL database. The database was checked and contained the 12 application tables plus Alembic's `alembic_version` table.

## Environment Configuration

Settings are defined in `app/core/config.py` using Pydantic Settings.

Current defaults:

| Setting | Default |
|---|---|
| `app_env` | `development` |
| `database_url` | `postgresql+psycopg://postgres:postgres@localhost:5432/leave_expense` |
| `random_seed` | `20261022` |
| `openai_api_key` | Not set |
| `llm_model` | Not set |

The settings class reads values from a `.env` file and ignores extra environment variables.

### Example `.env`

Create a `.env` file in the backend directory if you need to override the defaults:

```dotenv
APP_ENV=development
DATABASE_URL=postgresql+psycopg://postgres:YOUR_LOCAL_PASSWORD@localhost:5432/leave_expense
RANDOM_SEED=20261022
```

Replace `YOUR_LOCAL_PASSWORD` with your local PostgreSQL password. Keep `.env` out of version control, and never commit real passwords or API keys.

The database URL above is a development default, not a recommended production credential.

## Setup and Run

The commands below assume Windows Command Prompt and an existing Docker Compose configuration for PostgreSQL.

### 1. Start PostgreSQL

From the project root:

```cmd
cd C:\leave-expense-automation
docker compose up -d db
```

Check the container status:

```cmd
docker compose ps
```

### 2. Open the backend directory

```cmd
cd C:\leave-expense-automation\backend
```

### 3. Install dependencies

If the dependencies are not already installed:

```cmd
python -m pip install -r requirements.txt
```

### 4. Apply database migrations

```cmd
alembic upgrade head
```

The initial migration revision recorded in the database is:

```text
7cca772ec3f5
```

If the database is already migrated, Alembic should report that it is up to date.

### 5. Start the FastAPI server

```cmd
python -m uvicorn app.main:app --reload
```

The development server should be available at:

- API base: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI schema: http://127.0.0.1:8000/openapi.json

Stop the server with `Ctrl+C`.

## Current API

### Health Check

**Endpoint:** `GET /health`

Expected response:

```json
{
  "status": "ok"
}
```

This endpoint has been tested successfully using:

```cmd
curl http://127.0.0.1:8000/health
```

## Employee API

The employee schemas have been created in `app/schemas/employees.py` and passed Python syntax compilation and import checks.

The initial employee API is intended to support the following endpoints:

| Method | Path | Intended behavior |
|---|---|---|
| `GET` | `/api/v1/employees` | List employees with pagination and optional department/country filters |
| `GET` | `/api/v1/employees/{employee_id}` | Retrieve one employee |
| `POST` | `/api/v1/employees` | Create an employee |
| `PATCH` | `/api/v1/employees/{employee_id}` | Update employee details |

The planned implementation includes:

- Pydantic request and response validation
- Database session dependency injection
- Duplicate employee number and email checks
- Validation of manager and cost-center references
- Employment date validation
- Appropriate HTTP error responses

**Status:** These routes must still be verified in the running application. Do not consider employee CRUD fully tested until route registration and database operations succeed.

## Verification So Far

The following checks have been performed successfully:

- All 12 SQLAlchemy models import successfully.
- The models are exported from `app/db/models/__init__.py`.
- The initial Alembic migration was applied successfully.
- PostgreSQL contains the expected application tables.
- `python -m pip check` reported no broken requirements.
- FastAPI started successfully.
- `GET /health` returned `{"status":"ok"}`.
- Employee Pydantic schemas compiled and imported successfully.

The following still need verification:

- Employee route registration
- Employee create, list, retrieve, and update operations
- Duplicate email and employee number handling
- Manager and cost-center reference validation
- Automated tests for success and failure cases

## Next Steps

1. Finish registering the employee router in FastAPI.
2. Run Python syntax checks and inspect registered routes.
3. Test employee CRUD operations against PostgreSQL.
4. Add automated tests for duplicate records, missing references, invalid dates, and nonexistent employees.
5. Implement leave policies, leave requests, and leave balances.
6. Implement expense claims, expense policies, and cost-center budget checks.
7. Implement approval routing, reimbursements, and audit events.
8. Add analytics and AI-assisted workflow capabilities.
9. Integrate the frontend and document end-to-end usage.

---

This README documents the project state reached before proceeding to the next development step. Update the status sections as features are implemented and tested.


=================================================================================================
# Leave & Expense Automation Platform

A full-stack workflow automation application designed to manage employee leave requests, expense claims, approval workflows, policy validation, reimbursements, audit logs, analytics, and AI-assisted business operations.

The project is being developed with a Python-focused backend and a PostgreSQL database, with plans for a web frontend and AI-powered capabilities.

## Project Status

**Current milestone:** Backend foundation and Employee API implementation.

Completed and verified:
- FastAPI application setup
- PostgreSQL database running through Docker
- SQLAlchemy models and Alembic database migrations
- Employee Pydantic schemas
- Employee CRUD endpoints
- Employee creation and retrieval
- Employee updates
- Duplicate employee number validation
- Duplicate email validation
- Employment date validation
- Manager reference validation
- Cost-center reference validation

Automated tests are the next planned step.

## Technology Stack

### Backend
- Python
- FastAPI
- SQLAlchemy
- Alembic
- Pydantic
- Pydantic Settings
- Uvicorn

### Database
- PostgreSQL 16
- Docker
- Docker Compose

### API Documentation
- OpenAPI
- Swagger UI
- ReDoc

### Planned Frontend
- React
- Vite
- JavaScript or TypeScript
- REST API integration

### Planned AI Capabilities
- AI-assisted workflow support
- Retrieval-Augmented Generation (RAG)
- Policy and document question answering
- AI-assisted business insights

These frontend and AI capabilities are planned and are not yet verified as implemented.

## Project Structure

```text
leave-expense-automation/
├── README.md
├── docker-compose.yml
└── backend/
    ├── alembic/
    ├── alembic.ini
    ├── app/
    │   ├── __init__.py
    │   ├── main.py
    │   ├── ai/
    │   ├── api/
    │   │   └── v1/
    │   │       ├── router.py
    │   │       └── endpoints/
    │   │           ├── ai.py
    │   │           ├── analytics.py
    │   │           ├── approvals.py
    │   │           ├── audit.py
    │   │           ├── employees.py
    │   │           ├── expenses.py
    │   │           ├── leave.py
    │   │           └── reimbursements.py
    │   ├── core/
    │   │   ├── config.py
    │   │   ├── logging.py
    │   │   └── security.py
    │   ├── db/
    │   │   ├── base.py
    │   │   ├── session.py
    │   │   └── models/
    │   │       ├── __init__.py
    │   │       └── models.py
    │   ├── repositories/
    │   ├── rules/
    │   ├── schemas/
    │   │   └── employees.py
    │   ├── services/
    │   ├── utils/
    │   └── workflows/
    ├── requirements.txt
    └── tests/
```

Some modules and endpoint files are placeholders for future development.

## Database Models

The application currently defines the following 12 SQLAlchemy models:

| Model | Purpose |
|---|---|
| Employee | Employee information and reporting relationships |
| LeavePolicy | Rules governing employee leave |
| LeaveBalance | Employee leave balances |
| LeaveRequest | Employee leave applications |
| ExpensePolicy | Expense eligibility and reimbursement rules |
| ExpenseClaim | Employee expense claims |
| ExpenseLine | Individual items within an expense claim |
| CostCenter | Departmental or organizational cost centers |
| ApprovalRule | Conditions determining approval requirements |
| ApprovalStep | Individual steps in an approval workflow |
| Reimbursement | Reimbursement records |
| AuditEvent | Records of important application events |

Database tables and the Alembic migration have been created. The Employee API has been tested against the running database.

## Environment Configuration

The backend settings are defined in:

```text
backend/app/core/config.py
```

Current default settings include:

```python
app_env = "development"
database_url = "postgresql+psycopg://postgres:postgres@localhost:5432/leave_expense"
random_seed = 20261022
```

Optional AI configuration:

```python
openai_api_key = None
llm_model = None
```

The application uses Pydantic Settings to load configuration, including values from a `.env` file.

For local development, create a `backend/.env` file if needed and configure the database connection and optional AI settings. Do not commit API keys or other secrets to version control.

## Prerequisites

Install or configure the following:

- Python 3.13
- Docker Desktop
- Docker Compose
- Git
- A terminal such as Windows Command Prompt or PowerShell

The commands below use Windows Command Prompt.

## Setup and Run the Backend

### 1. Open the project

```cmd
cd C:\leave-expense-automation
```

### 2. Start PostgreSQL

Start the database using Docker Compose:

```cmd
docker compose up -d
```

Check the running containers:

```cmd
docker ps
```

The PostgreSQL container should be running and exposing port `5432`.

### 3. Open the backend directory

```cmd
cd C:\leave-expense-automation\backend
```

### 4. Install dependencies

```cmd
python -m pip install -r requirements.txt
```

Check dependency consistency:

```cmd
python -m pip check
```

The previously verified result was:

```text
No broken requirements found.
```

### 5. Apply database migrations

```cmd
alembic upgrade head
```

The database migration has previously been applied successfully. The recorded migration revision was:

```text
7cca772ec3f5
```

If the database is already up to date, Alembic should report that no additional migration is required.

### 6. Start the FastAPI server

```cmd
python -m uvicorn app.main:app --reload
```

Keep this terminal open while testing the API.

### 7. Verify the health endpoint

Open another terminal and run:

```cmd
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok"
}
```

## API Documentation

When the backend server is running, access:

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- OpenAPI schema: http://127.0.0.1:8000/openapi.json

Swagger UI can be used to execute API requests and inspect responses.

## Employee API

Base URL:

```text
http://127.0.0.1:8000/api/v1
```

### Available Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/employees` | List employees |
| GET | `/employees/{employee_id}` | Retrieve one employee |
| POST | `/employees` | Create an employee |
| PATCH | `/employees/{employee_id}` | Update an employee |

### List Employees

Request:

```http
GET /api/v1/employees
```

Supported query parameters:

| Parameter | Description |
|---|---|
| `offset` | Number of records to skip; default `0` |
| `limit` | Maximum number of records; default `50`, maximum `200` |
| `department` | Optional exact department filter |
| `country` | Optional two-character country filter |

Example:

```http
GET /api/v1/employees?department=Engineering&country=IN
```

A successful request returns HTTP `200 OK` and a JSON array of employee records.

### Retrieve One Employee

Request:

```http
GET /api/v1/employees/{employee_id}
```

Returns HTTP `200 OK` when the employee exists, or HTTP `404 Not Found` when the employee does not exist.

### Create an Employee

Request:

```http
POST /api/v1/employees
```

Example request body:

```json
{
  "employee_number": "EMP-TEST-001",
  "first_name": "Test",
  "last_name": "Employee",
  "email": "test.employee@example.com",
  "job_title": "Software Developer",
  "department": "Engineering",
  "country": "IN",
  "currency": "INR",
  "manager_id": null,
  "cost_center_id": null,
  "employment_start_date": "2026-10-28",
  "employment_end_date": null,
  "employment_status": "ACTIVE",
  "is_approver": false,
  "attributes": {}
}
```

A successful request returns HTTP `201 Created`, including the generated employee ID and timestamps.

### Update an Employee

Request:

```http
PATCH /api/v1/employees/{employee_id}
```

Example request body:

```json
{
  "job_title": "Senior Software Developer"
}
```

A successful request returns HTTP `200 OK` with the updated employee information.

## Employee Validation Rules

The Employee API implements and has manually verified the following checks:

| Validation | Expected status | Verified |
|---|---:|---|
| Create an employee | `201` | Yes |
| List employees | `200` | Yes |
| Retrieve an employee by ID | `200` | Yes |
| Update an employee | `200` | Yes |
| Duplicate employee number | `409` | Yes |
| Duplicate email address | `409` | Yes |
| End date earlier than start date | `422` | Yes |
| Nonexistent manager reference | `400` | Yes |
| Nonexistent cost-center reference | `400` | Yes |

The duplicate and reference validations prevent the tested invalid employee records from being created.

Some error responses are currently displayed as **Undocumented** in Swagger UI because the corresponding status codes have not yet been explicitly declared in the endpoint response documentation. The tested runtime validation behavior works as expected.

## Employee Data Model

Employee records include:

- Unique employee ID
- Unique employee number
- First and last name
- Email address
- Job title
- Department
- Country and currency
- Optional manager reference
- Optional cost-center reference
- Employment start and end dates
- Employment status
- Approver flag
- JSON attributes
- Creation and update timestamps

The generated employee ID uses the `EMP-` prefix followed by a UUID-derived identifier.

## Testing Progress

The Employee API has been manually tested through Swagger UI and `curl`.

Successful checks include:

1. Creating an employee.
2. Listing employees.
3. Retrieving a specific employee.
4. Updating an employee's job title.
5. Rejecting a duplicate employee number.
6. Rejecting a duplicate email address.
7. Rejecting invalid employment dates.
8. Rejecting nonexistent manager references.
9. Rejecting nonexistent cost-center references.

Automated tests have not yet been implemented or verified. The next step is to inspect the existing test dependencies and `backend/tests` directory, then add repeatable automated tests.

## Current Limitations

- Employee endpoints are implemented, but the other business endpoints remain future work or placeholders.
- Authentication and authorization integration for API routes has not yet been verified.
- Automated testing is pending.
- Frontend implementation is pending.
- Leave request and expense claim business workflows are pending.
- Approval workflow execution is pending.
- AI/RAG functionality is pending.
- API error response documentation needs improvement.

## Planned Development Roadmap

### Phase 1 — Backend Foundation
- [x] FastAPI application
- [x] PostgreSQL database
- [x] SQLAlchemy models
- [x] Alembic migration
- [x] Database session management
- [x] Employee schemas
- [x] Employee CRUD API
- [x] Manual Employee API validation
- [ ] Automated backend tests
- [ ] Explicit API error response documentation

### Phase 2 — Employee and Policy Management
- [ ] Complete employee management features
- [ ] Leave policy management
- [ ] Leave balance management
- [ ] Expense policy management
- [ ] Cost-center management

### Phase 3 — Leave Workflow
- [ ] Submit leave requests
- [ ] Validate leave eligibility and balances
- [ ] Apply approval rules
- [ ] Approve or reject leave requests
- [ ] Update leave balances
- [ ] Record audit events

### Phase 4 — Expense Workflow
- [ ] Submit expense claims
- [ ] Validate expense policies
- [ ] Process expense lines
- [ ] Apply approval rules
- [ ] Track reimbursement status
- [ ] Record audit events

### Phase 5 — Analytics and AI
- [ ] Workflow analytics and reports
- [ ] AI-assisted policy question answering
- [ ] Retrieval-Augmented Generation (RAG)
- [ ] AI-assisted workflow insights

### Phase 6 — Frontend and Integration
- [ ] Build React/Vite frontend
- [ ] Integrate frontend with FastAPI
- [ ] Add authentication and role-based access
- [ ] Add end-to-end tests
- [ ] Prepare deployment configuration

## Current Development Checkpoint

The project has a functioning FastAPI backend connected to PostgreSQL. Employee creation, listing, retrieval, updating, and the tested business-rule validations are working.

**Next action:** Inspect the backend test dependencies and existing test directory, then implement automated tests for the Employee API before proceeding to additional business modules.

---

*This README describes the verified project state as of October 28, 2026. Features marked as planned or pending should not be considered implemented until they have been developed and tested.*

===========================================================================================



# Leave & Expense Automation

A backend application for automating employee leave and expense workflows with policy-aware validation, structured APIs, and reliable database operations.

The project is being developed with a Python-first backend to demonstrate API development, database design, business-rule validation, automated testing, and workflow automation.

## Project Overview

Organizations need a consistent way to manage employee records, leave requests, approvals, expense claims, and policy compliance. This project aims to provide a centralized backend for these operations.

### Current Progress

- [x] FastAPI application setup
- [x] API versioning with `/api/v1`
- [x] SQLAlchemy database models and session management
- [x] PostgreSQL database integration
- [x] Employee CRUD APIs
- [x] Employee filtering and pagination
- [x] Duplicate employee number and email validation
- [x] Manager and cost center reference validation
- [x] Employment date range validation
- [x] Automated employee API tests
- [x] All 23 employee API tests passing

Leave management, expense management, policy evaluation, approval workflows, and automation features are planned for subsequent development stages.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Primary backend and business logic |
| FastAPI | REST API development |
| Pydantic | Request and response validation |
| SQLAlchemy | ORM and database operations |
| PostgreSQL | Application database |
| Alembic | Database schema migrations |
| Pytest | Automated testing |
| SQLite | Isolated in-memory database for API tests |
| Docker | Database development environment |
| Ruff | Python linting and code quality |

## Current Project Structure

```text
leave-expense-automation/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── endpoints/
│   │   │       │   ├── employees.py
│   │   │       │   └── leave.py
│   │   │       └── router.py
│   │   ├── db/
│   │   │   ├── base.py
│   │   │   ├── session.py
│   │   │   └── models/
│   │   │       └── models.py
│   │   ├── schemas/
│   │   │   └── employees.py
│   │   └── main.py
│   └── tests/
│       ├── conftest.py
│       └── test_employees.py
├── pyproject.toml
└── README.md
```

*Note: This is a simplified view of the current project. Other existing configuration, migration, and database files may not be shown.*

## Implemented Features

### 1. Employee Management API

The employee management module provides endpoints for creating, retrieving, listing, and updating employee records.

**Implemented capabilities:**

- Create employee records.
- Retrieve an employee by ID.
- List employees with pagination.
- Filter employees by department and country.
- Update existing employee details.
- Validate required fields and field lengths.
- Prevent duplicate employee numbers and email addresses.
- Validate manager and cost center references.
- Prevent an employee from being their own manager.
- Validate employment start and end dates.
- Reject invalid updates, including attempts to set required fields to `null`.

### 2. Employee Data Model

Employee records support the following information:

- Employee number and employee ID
- First name and last name
- Email address and job title
- Department, country, and currency
- Manager and cost center references
- Employment start and end dates
- Employment status
- Approver eligibility
- Additional attributes
- Creation and update timestamps

### 3. API Validation

The backend uses Pydantic schemas and application-level validation to check incoming requests.

Validation covers:

- Required fields
- Minimum and maximum field lengths
- Country and currency field lengths
- Duplicate employee identifiers and email addresses
- Invalid employment date ranges
- Invalid manager and cost center references
- Invalid pagination parameters
- Invalid update payloads

### 4. Database and Testing Setup

SQLAlchemy manages database operations, while PostgreSQL serves as the application database.

Automated API tests use an isolated, in-memory SQLite database. This allows the employee API test suite to run without depending on the running PostgreSQL container.

The shared pytest fixtures create the test schema, provide a test database session, override the FastAPI database dependency, and clean up the test engine afterward.

## API Endpoints Implemented

Base URL:

```text
/api/v1
```

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/employees` | Create an employee |
| GET | `/api/v1/employees` | List employees, filter, and paginate |
| GET | `/api/v1/employees/{employee_id}` | Retrieve an employee |
| PUT | `/api/v1/employees/{employee_id}` | Update an employee |

The application also provides a health check:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Check whether the API is running |

These routes represent the implemented employee API functionality; additional endpoints will be documented as their modules are completed.

## Running the Backend

Run the following commands from the backend directory:

```cmd
cd C:\leave-expense-automation\backend
```

Activate your virtual environment if you are using one:

```cmd
.venv\Scripts\activate
```

Install the project's dependencies using its existing dependency configuration.

Start the API server:

```cmd
python -m uvicorn app.main:app --reload
```

The local development server should be available at:

```text
http://127.0.0.1:8000
```

### API Documentation

FastAPI automatically generates interactive API documentation.

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- Health check: http://127.0.0.1:8000/health

## Running Automated Tests

From `C:\leave-expense-automation\backend`, execute:

```cmd
python -m pytest -v
```

To collect tests without executing them:

```cmd
python -m pytest --collect-only -q
```

To run only the employee API tests:

```cmd
python -m pytest tests/test_employees.py -v
```

### Current Test Results

```text
23 passed
0 failed
0 warnings
```

The employee test suite verifies successful API operations, not-found responses, duplicate records, invalid references, date validation, filtering, pagination, and invalid request payloads.

These results reflect the current employee API test suite and do not indicate that the entire planned application has been completed.

## Planned Development Roadmap

The following modules are planned and are not yet represented as completed features in this README.

- [ ] **Leave management:** Leave request creation, retrieval, updates, and status tracking.
- [ ] **Leave policies:** Policy configuration, eligibility checks, leave balance calculations, and business-rule validation.
- [ ] **Approval workflows:** Manager assignment, approval and rejection, and approval history.
- [ ] **Expense management:** Expense submissions, categories, amounts, receipts, and claim status.
- [ ] **Expense policies:** Spending limits, eligibility rules, and policy violation detection.
- [ ] **Workflow automation:** Automated actions and notifications based on workflow events.
- [ ] **Reporting and analytics:** Leave summaries, expense totals, approval metrics, and operational reports.
- [ ] **Authentication and authorization:** Secure user access and role-based permissions.
- [ ] **Expanded testing:** Unit tests, integration tests, edge cases, and end-to-end workflow tests.
- [ ] **Deployment:** Production configuration, logging, monitoring, and deployment documentation.

## Engineering Approach

The project follows these principles:

- **Modular architecture:** Keep API routes, schemas, database models, and business logic organized.
- **Validation first:** Reject invalid data before it causes inconsistent application state.
- **Database integrity:** Use constraints and relationships to protect data consistency.
- **Automated testing:** Test both successful operations and expected failure cases.
- **Maintainability:** Prefer reusable functions, clear naming, and consistent API responses.
- **Incremental development:** Complete and test each module before expanding to the next workflow.

## Project Status

**Current milestone:** Employee management API and automated tests.

The next development step is to inspect and test the leave management module, then continue implementing and testing the remaining business workflows.

===========================================================================================