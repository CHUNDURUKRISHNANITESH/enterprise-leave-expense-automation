"""Generate policy-compliant expense claims with unique receipt metadata."""
from __future__ import annotations
import random
from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from .config import GeneratorConfig


def generate_expense_data(master: dict[str, list[dict[str, Any]]], config: GeneratorConfig):
    rng = random.Random(config.seed + 29)
    policies = {(p['country'], p['category']): p for p in master['expense_policies']}
    employees = [e for e in master['employees'] if e['manager_id'] and e['cost_center_id']]
    if not employees and config.expense_claim_count:
        raise ValueError('No eligible expense requesters')
    claims, lines, decisions = [], [], []
    for i in range(1, config.expense_claim_count + 1):
        e = rng.choice(employees)
        eligible_policies = [p for p in master['expense_policies'] if p['country'] == e['country']]
        policy = rng.choice(eligible_policies)
        count = rng.randint(config.min_lines_per_claim, config.max_lines_per_claim)
        claim_id = f'EXP-GEN-2026-{i:06d}'
        expense_date = date(2026, 1, 5) + timedelta(days=rng.randrange(270))
        total = Decimal('0.00')
        for n in range(1, count+1):
            unit = Decimal(rng.randint(100, 700))
            quantity = Decimal(rng.randint(1, 2))
            amount = unit * quantity
            total += amount
            receipt_hash = f'generated-receipt-{i:06d}-{n:02d}'
            lines.append(dict(id=f'EXPL-GEN-{i:06d}-{n:02d}', claim_id=claim_id, line_number=n,
                              category=policy['category'], description=f'Synthetic {policy["category"].lower()} expense',
                              expense_date=expense_date.isoformat(), quantity=str(quantity), unit_amount=str(unit),
                              line_amount=str(amount), currency=e['currency'],
                              receipt_uri=f'https://example.invalid/receipts/{receipt_hash}.pdf', receipt_hash=receipt_hash,
                              metadata={'synthetic': True}))
        # Per-line and total limits are checked, not randomised.
        valid = total <= Decimal(policy['max_amount']) and all(Decimal(x['line_amount']) <= Decimal(policy['per_item_limit']) for x in lines[-count:])
        # A manager decision is explicitly simulated only after policy checks pass.
        status = 'APPROVED' if valid and total <= Decimal('5000.00') else 'REJECTED'
        claims.append(dict(id=claim_id, employee_id=e['id'], cost_center_id=e['cost_center_id'],
                           expense_date=expense_date.isoformat(), submitted_at='2026-10-28T00:00:00+00:00',
                           description='Synthetic expense claim', business_purpose='Business operations', merchant='Synthetic Merchant',
                           country=e['country'], currency=e['currency'], total_amount=str(total), status=status,
                           receipt_uri=lines[-count]['receipt_uri'], receipt_hash=lines[-count]['receipt_hash'],
                           decision_reason='Manager approved' if status=='APPROVED' else 'Manager rejected or policy violation',
                           anomaly_flags=[], metadata={'synthetic': True}))
        decisions.append((claim_id, e, status))
    return {'expense_claims': claims, 'expense_lines': lines}, decisions
