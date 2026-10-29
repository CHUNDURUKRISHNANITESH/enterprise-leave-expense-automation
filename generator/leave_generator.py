"""Deterministic, policy-aware synthetic leave transactions."""
from __future__ import annotations
import random
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from .config import GeneratorConfig
from .master_data import generate_master_data


def working_days(start: date, end: date) -> int:
    return sum((start + timedelta(days=i)).weekday() < 5 for i in range((end-start).days+1))


def generate_leave_data(master: dict[str, list[dict[str, Any]]], config: GeneratorConfig):
    rng = random.Random(config.seed + 11)
    policies = {(p['country'], p['leave_type']): p for p in master['leave_policies']}
    candidates = [e for e in master['employees'] if e['manager_id'] and any(k[0] == e['country'] for k in policies)]
    if not candidates and config.leave_request_count:
        raise ValueError('No eligible leave requesters')
    balances, requests, decisions = [], [], []
    for e in master['employees']:
        for p in master['leave_policies']:
            if e['country'] != p['country']:
                continue
            balances.append(dict(id=f"LB-GEN-{e['id']}-{p['id']}", employee_id=e['id'], leave_policy_id=p['id'], period_year=2026,
                                 entitled_days=p['annual_entitlement'], used_days='0.00', pending_days='0.00',
                                 carryover_days='0.00', adjustment_days='0.00', notes='Synthetic annual entitlement'))
    lookup = {(b['employee_id'], b['leave_policy_id']): b for b in balances}
    for i in range(1, config.leave_request_count + 1):
        e = rng.choice(candidates)
        choices = [p for p in master['leave_policies'] if p['country'] == e['country']]
        p = rng.choice(choices)
        start = date(2026, 1, 5) + timedelta(days=rng.randrange(270))
        while start.weekday() >= 5:
            start += timedelta(days=1)
        duration = rng.randint(1, 4)
        end = start + timedelta(days=duration-1)
        days = working_days(start, end)
        b = lookup[(e['id'], p['id'])]
        available = Decimal(b['entitled_days']) - Decimal(b['used_days']) - Decimal(b['pending_days'])
        # Decisions derive from remaining balances and a reproducible, explicit manager decision simulation.
        eligible = available >= days and days <= (p['max_consecutive_days'] or 999)
        decision = 'APPROVED' if eligible and days <= 2 else 'REJECTED'
        if decision == 'APPROVED':
            b['used_days'] = str(Decimal(b['used_days']) + days)
        elif decision == 'NEEDS_REVIEW':
            decision = 'REJECTED'  # insufficient balance is a rule-derived rejection
        elif decision == 'REJECTED':
            pass
        rid = f'LVE-GEN-2026-{i:06d}'
        requests.append(dict(id=rid, employee_id=e['id'], leave_policy_id=p['id'], start_date=start.isoformat(),
                             end_date=end.isoformat(), requested_days=f'{days:.2f}', reason='Synthetic leave request',
                             status=decision, submitted_at='2026-10-28T00:00:00+00:00',
                             decided_at='2026-10-28T00:01:00+00:00', decision_reason=('Balance and policy checks passed' if decision=='APPROVED' else 'Manager rejected or insufficient balance'),
                             anomaly_flags=[], metadata={'synthetic': True}))
        decisions.append((rid, e, decision))
    return {'leave_balances': balances, 'leave_requests': requests}, decisions
