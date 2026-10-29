# Fast-track workflow update

Implemented in this copy:

- Leave Management: Create Draft (existing), Submit Draft with confirmation and refresh.
- Expense Management: list, details, create single-line draft, submit draft; cost center, receipt, currency and policy validations remain enforced by FastAPI.
- Approval Inbox: assigned pending expense and leave steps, approve/reject with reason.
- Reimbursements: authenticated list and lookup; finance roles can initiate from approved claims, process, mark paid or failed.
- AI Policy Assistant: authenticated `/api/v1/ai/ask`, retrieves country-specific leave and expense policy records from PostgreSQL; with `OPENAI_API_KEY` optionally generates source-grounded LLM responses. Without the key it returns clearly labeled matching records (retrieval-only, not AI-generated answers).
- New page CSS lives in `frontend/src/css/`.

## Setup

1. Preserve the existing PostgreSQL databases. No migrations or seed scripts are run by this update.
2. In backend CMD: `set "DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/leave_expense_synthetic"` and set your own `JWT_SECRET_KEY` matching the existing test environment.
3. Optional LLM: set `OPENAI_API_KEY` in backend environment, and optionally `LLM_MODEL`. Never commit these values.
4. Run backend: `python -m uvicorn app.main:app --reload --port 8000`.
5. In frontend: `npm ci` then `npm run build`, then `npm run dev`.
6. Test with appropriate employee, approver and HR/ADMIN accounts. Some actions require seeded active cost centers and applicable policies.

## Limitations and verification

- TypeScript build could not be run in this isolated environment: frontend dependencies were absent and npm offline cache was incomplete. Run `npm ci && npm run build` locally.
- Backend Python files were syntax-checked, but live database integration and role workflows require your running PostgreSQL and authenticated accounts.
- Expense creation UI currently supports one line item per claim; backend accepts up to 10. Receipt is metadata URI, not a binary upload.
- Reimbursement list is capped at 200 recent records; add server pagination for production.
- AI retrieval is lexical ranking of database policy fields, not embedding-based vector RAG. The optional LLM call is grounded in retrieved records; production RAG ingestion/embeddings and testing remain future work.
- No test database or original database was modified while preparing this ZIP.
