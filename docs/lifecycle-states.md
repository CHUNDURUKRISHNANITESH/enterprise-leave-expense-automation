# Lifecycle States

Suggested claim states: DRAFT, SUBMITTED, PENDING_APPROVAL, NEEDS_REVIEW, APPROVED, REJECTED, REIMBURSEMENT_PENDING, REIMBURSED.

Define permitted transitions centrally. Persist each transition as an audit event; do not overwrite historical decisions. Reimbursement must not exist before final approval.
