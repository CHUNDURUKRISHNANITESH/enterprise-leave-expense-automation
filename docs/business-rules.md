# Business Rules

- Calculate derived values from source records; do not assign them independently at random.
- Route approvals by configured country, category, amount, manager hierarchy, and authority.
- Prevent requester self-approval.
- Validate employment dates, leave overlap/balance, receipt rules, policy limits, and cost centers.
- Flag suspected split claims and duplicate receipt hashes for review.
- Create reimbursement records only after final approval; enforce idempotency.
- Record decision reasons and append audit events for state changes.
- Treat anomalies as explicit labeled cases, not silent corruption.
