# Phase 4 integration — master-data generator (Part 1)

This package is integrated into the original project under `generator/`.
It preserves the FastAPI backend and existing tests. The master-data generator currently produces **JSON only**; it does not insert data into PostgreSQL.

From the project root, with your existing backend virtual environment activated:

```cmd
python -m pip install Faker
python -m generator.run_master_data --seed 20261022 --employees 400 --leave-policies 6
```

Output: `generated_data/master_data.json`. This contains 400 employees, 18 cost centers, 6 leave policies, 9 expense policies, and 3 approval rules. Generated data is deterministic for the same seed.

**Not yet implemented:** leave/expense transaction generators, SQLAlchemy database loader, rule-derived decisions, and complete Phase 4 verification. Do not run this against production data.

**Packaging:** The Windows virtual environment, local secrets (`.env`), caches and generated files were deliberately excluded. Reuse your existing `.venv` and `.env` locally; do not overwrite or delete your working directory without backing it up.
