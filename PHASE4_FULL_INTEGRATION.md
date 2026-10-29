# Phase 4 — Full synthetic data generation (integrated)

From the **project root**, with `backend/.venv` activated:

```cmd
python -m generator.cli --seed 20261022 --employees 400 --leave-policies 6 --leave-requests 800 --expense-claims 1000
```

Output: `generated_data/full_dataset.json`. This operation **never touches PostgreSQL**.

The generator produces employees, cost centers, leave and expense policies, approval rules, leave balances, leave requests, expense claims/lines, manager approval steps, and append-only synthetic audit events. It validates foreign keys, totals, working days and approval relationships. Manager decisions follow explicit synthetic thresholds (leave requests up to 2 working days with sufficient balance; expense totals up to 5,000 within policy limits); **they are not replayed through FastAPI's live decision endpoints**. Generated records are illustrative test fixtures, not an authoritative simulation of all runtime policy rules. The default manager-only approval route is represented; no reimbursements are generated.

## Database loader — separate database ONLY

The loader requires an **explicitly selected, migrated, empty PostgreSQL database ending `_synthetic`**. It refuses the existing `leave_expense` database and refuses nonempty domain tables. It does not create a database, run migrations, drop tables, or overwrite records. This protects your Phase 3 records.

Create a separate database using your existing PostgreSQL service (from the project root):

```cmd
docker compose exec db psql -U postgres -d postgres -c "CREATE DATABASE leave_expense_synthetic;"
```

Run your project's Alembic migrations against that database, by temporarily setting `DATABASE_URL` **in the migration CMD session** (do not edit the persistent `.env`):

```cmd
cd backend
set "DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/leave_expense_synthetic"
alembic upgrade head
cd ..
```

In a fresh CMD session, from the project root, set only the generator-specific URL:

```cmd
set "GENERATOR_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/leave_expense_synthetic"
python -m generator.load_postgres --confirm-db leave_expense_synthetic
python -m generator.load_postgres --confirm-db leave_expense_synthetic --write
```

The first command is a dry run. The second performs a single transaction; errors roll back all inserts. The generated employees have no login accounts by default. The production application continues using its configured database until you explicitly configure it otherwise.

## Verify counts

```cmd
docker compose exec db psql -U postgres -d leave_expense_synthetic -c "SELECT (SELECT COUNT(*) FROM employees) AS employees, (SELECT COUNT(*) FROM leave_requests) AS leave_requests, (SELECT COUNT(*) FROM expense_claims) AS expense_claims, (SELECT COUNT(*) FROM approval_steps) AS approval_steps;"
```

## Limits

- Generated leave accruals use annual entitlements and Monday–Friday business days, not a full month-by-month accrual schedule.
- Generated manager approvals and audit events are deterministic fixtures, not calls to the backend's HTTP endpoints. For authoritative routing/transition tests, continue using your FastAPI integration suite.
- No synthetic anomalies or ground-truth labeling have been implemented; those are separate optional extensions.
