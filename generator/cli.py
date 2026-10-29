"""Phase 4 synthetic generator; safe by default (JSON only)."""
import argparse
from .config import GeneratorConfig
from .master_data import generate_master_data
from .leave_generator import generate_leave_data
from .expense_generator import generate_expense_data
from .approval_generator import generate_approvals
from .validators import validate_dataset
from .exporters import export_json

def generate(config):
    master = generate_master_data(config)
    leaves, ld = generate_leave_data(master, config)
    expenses, ed = generate_expense_data(master, config)
    approvals = generate_approvals(master, ld, ed)
    data = {**master, **leaves, **expenses, **approvals}
    # Budget commitments represent approved/pending expense amounts; rejected claims release reservations.
    amounts = {center['id']: 0 for center in data['cost_centers']}
    from decimal import Decimal
    committed = {key: Decimal('0.00') for key in amounts}
    for claim in data['expense_claims']:
        if claim['status'] in ('APPROVED','PENDING_APPROVAL'):
            committed[claim['cost_center_id']] += Decimal(claim['total_amount'])
    for center in data['cost_centers']:
        center['committed_amount'] = str(committed[center['id']])
    validate_dataset(data)
    return data

def main():
    parser = argparse.ArgumentParser(description='Generate and validate synthetic leave/expense data (JSON; no database writes).')
    parser.add_argument('--seed', type=int, default=20261022)
    parser.add_argument('--employees', type=int, default=400)
    parser.add_argument('--leave-policies', type=int, default=6)
    parser.add_argument('--leave-requests', type=int, default=800)
    parser.add_argument('--expense-claims', type=int, default=1000)
    parser.add_argument('--output', default='generated_data/full_dataset.json')
    args = parser.parse_args()
    config = GeneratorConfig(seed=args.seed, employee_count=args.employees, leave_policy_count=args.leave_policies,
                             leave_request_count=args.leave_requests, expense_claim_count=args.expense_claims)
    data = generate(config)
    path = export_json(data, args.output)
    print('Saved:', path)
    for name, count in validate_dataset(data).items():
        print(f'{name}: {count}')
    print('Validation: PASSED; PostgreSQL: NOT MODIFIED')

if __name__ == '__main__':
    main()
