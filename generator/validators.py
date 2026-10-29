"""Cross-table invariants for generated datasets."""
from collections import Counter
from decimal import Decimal
from datetime import date, timedelta


def validate_dataset(data):
    errors = []
    ids = {}
    for name, rows in data.items():
        values = [r['id'] if 'id' in r else r['event_id'] for r in rows]
        if len(values) != len(set(values)):
            errors.append(f'{name}: duplicate primary keys')
        ids[name] = set(values)
    for name, fk, target in [('employees','manager_id','employees'), ('employees','cost_center_id','cost_centers'),
                             ('cost_centers','owner_employee_id','employees'), ('leave_balances','employee_id','employees'),
                             ('leave_balances','leave_policy_id','leave_policies'), ('leave_requests','employee_id','employees'),
                             ('leave_requests','leave_policy_id','leave_policies'), ('expense_claims','employee_id','employees'),
                             ('expense_claims','cost_center_id','cost_centers'), ('expense_lines','claim_id','expense_claims'),
                             ('approval_steps','approver_employee_id','employees')]:
        for row in data[name]:
            if row.get(fk) is not None and row[fk] not in ids[target]:
                errors.append(f'{name}: missing {target} reference {row[fk]}')
    claim_by_id = {c['id']: c for c in data['expense_claims']}
    totals = Counter()
    for line in data['expense_lines']:
        totals[line['claim_id']] += Decimal(line['line_amount'])
        if Decimal(line['quantity']) * Decimal(line['unit_amount']) != Decimal(line['line_amount']):
            errors.append(f"Expense arithmetic mismatch {line['id']}")
    for cid, claim in claim_by_id.items():
        if totals[cid] != Decimal(claim['total_amount']):
            errors.append(f'Claim total mismatch {cid}')
    for r in data['leave_requests']:
        start, end = date.fromisoformat(r['start_date']), date.fromisoformat(r['end_date'])
        count = sum((start+timedelta(days=i)).weekday()<5 for i in range((end-start).days+1))
        if count != Decimal(r['requested_days']):
            errors.append(f"Leave working-day mismatch {r['id']}")
    step_refs = Counter((s['leave_request_id'] or s['expense_claim_id']) for s in data['approval_steps'])
    for name in ('leave_requests','expense_claims'):
        for row in data[name]:
            if step_refs[row['id']] != 1:
                errors.append(f"Missing or duplicate approval step {row['id']}")
    if errors:
        raise ValueError('Dataset validation failed:\n'+'\n'.join(errors[:25]))
    return {name: len(rows) for name, rows in data.items()}
