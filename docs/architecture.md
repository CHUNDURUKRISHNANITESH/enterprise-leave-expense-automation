# Architecture

- React + TypeScript frontend calls the FastAPI REST API.
- FastAPI coordinates repositories, deterministic business rules, and workflow services.
- PostgreSQL is the source of truth for master data, transactions, approval steps, reimbursements, and audit events.
- The AI/RAG module retrieves policy evidence and uses read-only backend tools to explain persisted decisions.
- The synthetic-data generator is a separate reproducible pipeline. Ground truth must never be exposed as an input feature.
