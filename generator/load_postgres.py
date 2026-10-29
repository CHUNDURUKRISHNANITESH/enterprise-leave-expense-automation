"""Opt-in, additive PostgreSQL loader; requires a dedicated *_synthetic database.

Never connects to the application's default database implicitly. No schema creation,
truncation, update of existing records, or migrations are performed here.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from sqlalchemy import create_engine, inspect, MetaData, Table, select, update, insert
from sqlalchemy.engine import make_url
from .validators import validate_dataset

ORDER = ('cost_centers', 'employees', 'leave_policies', 'expense_policies', 'approval_rules',
         'leave_balances', 'leave_requests', 'expense_claims', 'expense_lines', 'approval_steps', 'audit_events')


def load(data, url: str, *, confirm_db: str, write: bool = False):
    validate_dataset(data)
    target = make_url(url)
    dbname = target.database or ''
    if not dbname.endswith('_synthetic') or confirm_db != dbname:
        raise ValueError('Safety check: use a dedicated database ending _synthetic and --confirm-db with its exact name')
    if not write:
        return f'DRY RUN: validated {sum(map(len, data.values()))} rows; no database writes'
    if target.get_backend_name() != 'postgresql':
        raise ValueError('Only PostgreSQL is supported for writing')
    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.begin() as conn:
            schema = inspect(conn)
            missing = [name for name in ORDER if not schema.has_table(name)]
            if missing:
                raise ValueError(f'Apply existing Alembic migrations to {dbname} first; missing: {missing}')
            meta = MetaData()
            tables = {name: Table(name, meta, autoload_with=conn) for name in ORDER}
            # Do not mix with existing rows; dedicated DB must be empty of domain records.
            for name in ORDER:
                if conn.execute(select(tables[name]).limit(1)).first() is not None:
                    raise ValueError(f'{dbname}.{name} is not empty; loader refuses to modify existing records')
            # Cost-center owners reference employees; employee rows reference cost centers.
            for center in data['cost_centers']:
                conn.execute(insert(tables['cost_centers']).values(**{**center, 'owner_employee_id': None}))
            for name in ORDER[1:]:
                for row in data[name]:
                    conn.execute(insert(tables[name]).values(**row))
            for center in data['cost_centers']:
                conn.execute(update(tables['cost_centers']).where(tables['cost_centers'].c.id == center['id'])
                             .values(owner_employee_id=center['owner_employee_id']))
        return f'LOADED {sum(map(len, data.values()))} rows into {dbname}'
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description='Safely load validated JSON into a dedicated migrated PostgreSQL *_synthetic database.')
    parser.add_argument('--input', default='generated_data/full_dataset.json')
    parser.add_argument('--database-url', default=os.environ.get('GENERATOR_DATABASE_URL'))
    parser.add_argument('--confirm-db', required=True)
    parser.add_argument('--write', action='store_true', help='Required for any DB writes')
    args = parser.parse_args()
    if not args.database_url:
        parser.error('Set GENERATOR_DATABASE_URL or pass --database-url (dedicated *_synthetic DB)')
    data = json.loads(Path(args.input).read_text(encoding='utf-8'))
    print(load(data, args.database_url, confirm_db=args.confirm_db, write=args.write))

if __name__ == '__main__':
    main()
