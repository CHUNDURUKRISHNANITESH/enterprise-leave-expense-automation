# PostgreSQL model layer

The model layer is in `models.py`; `__init__.py` imports every mapped class so Alembic sees the full metadata.

## Tables and responsibilities

| Table | Purpose |
|---|---|
| `employees` | Employee profile, country/currency, employment dates, manager hierarchy and cost center |
| `leave_policies` | Versioned, country-specific leave entitlements and effective dates |
| `leave_balances` | Annual entitlement, carryover, adjustments, used and pending days; unique per employee/policy/year |
| `leave_requests` | Requested dates/days, lifecycle status, policy and anomaly flags |
| `expense_policies` | Versioned category/country limits, receipt rules and effective dates |
| `cost_centers` | Departmental budget and committed spend |
| `expense_claims` | Claim header, employee, cost center, total, receipt metadata and status |
| `expense_lines` | Individual claim lines, categories, amounts and receipt hashes |
| `approval_rules` | Effective-dated approval routing conditions |
| `approval_steps` | Ordered decision trail; each step belongs to exactly one leave request or expense claim |
| `reimbursements` | At most one reimbursement per claim, with unique idempotency key |
| `audit_events` | Append-only lifecycle events with before/after JSON snapshots and reasons |

## Important design choices

- IDs are strings to support the documented IDs (`EMP-000001`, `LVE-2026-000001`, `EXP-2026-000001`, `EXPL-<claim-id>-01`, `APR-<request-id>-01`, `RMB-2026-000001`).
- Amounts and leave days use `NUMERIC`, not floating point.
- `JSONB` is used on PostgreSQL for flexible policy, metadata and audit snapshots (with generic JSON fallback for other dialects).
- `LeaveBalance.available_days` is a computed Python property, not a separately mutable database column.
- Check constraints enforce local invariants. Business workflows must additionally validate date overlaps, current policy applicability, manager hierarchy, self-approval, claim splitting, duplicate receipt hashes, budget availability, and final-approval-before-reimbursement.
- `AuditEvent` is modeled without a foreign key to every possible business entity so it can capture all entity types uniformly. Treat it as append-only in service code and restrict UPDATE/DELETE at the database role/permission layer for production.
- `ExpenseClaim.total_amount` is stored as a submission snapshot; application services should reconcile it against the sum of `ExpenseLine.line_amount` before submission/approval.
- A database constraint alone cannot prove a reimbursement was created after final approval. The reimbursement service must check approval state in the same transaction; consider a PostgreSQL trigger if that invariant must be enforced against all database writers.

## Create schema

From the `backend/` directory, install requirements, configure `DATABASE_URL`, then run:

```bash
alembic revision --autogenerate -m "create leave and expense models"
alembic upgrade head
```

Review generated migrations before applying them in production. `Base.metadata.create_all()` is suitable only for quick local smoke tests, not as a replacement for migrations.
