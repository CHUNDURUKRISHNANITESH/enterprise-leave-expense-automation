"""Approval steps and append-only audit events for synthetic transactions."""
from __future__ import annotations
from datetime import datetime, timezone


def generate_approvals(master, leave_decisions, expense_decisions):
    steps, events = [], []
    employees = {e['id']: e for e in master['employees']}
    def event(entity_type, entity_id, event_type, actor, n, old=None, new=None):
        events.append(dict(event_id=f'EV-GEN-{len(events)+1:08d}', entity_type=entity_type, entity_id=entity_id,
                           event_type=event_type, actor_employee_id=actor, occurred_at=f'2026-10-28T00:00:{n:02d}+00:00',
                           old_values=old, new_values=new, reason='Synthetic rule-driven workflow',
                           correlation_id=entity_id, source='GENERATOR', extra={'synthetic': True}))
    for kind, decisions in [('LEAVE_REQUEST', leave_decisions), ('EXPENSE_CLAIM', expense_decisions)]:
        for entity_id, employee, decision in decisions:
            manager_id = employee['manager_id']
            if not manager_id or manager_id == employee['id'] or manager_id not in employees:
                raise ValueError(f'Invalid approver for {entity_id}')
            is_leave = kind == 'LEAVE_REQUEST'
            steps.append(dict(id=f'APR-{entity_id}-01', leave_request_id=entity_id if is_leave else None,
                              expense_claim_id=None if is_leave else entity_id, rule_id=None,
                              step_number=1, approver_employee_id=manager_id, approver_role=None,
                              status=decision, decision=decision, decision_reason='Synthetic manager decision',
                              assigned_at='2026-10-28T00:00:00+00:00', decided_at='2026-10-28T00:00:02+00:00',
                              is_required=True, decision_metadata={'synthetic': True}))
            prefix = 'LEAVE' if is_leave else 'EXPENSE'
            event(kind, entity_id, f'{prefix}_CREATED', employee['id'], 0, new={'status': 'DRAFT'})
            event(kind, entity_id, f'{prefix}_SUBMITTED', employee['id'], 1, old={'status':'DRAFT'}, new={'status':'PENDING_APPROVAL'})
            event(kind, entity_id, f'{prefix}_APPROVAL_STEP_{decision}', manager_id, 2,
                  old={'status':'PENDING_APPROVAL'}, new={'status':decision})
    return {'approval_steps': steps, 'audit_events': events}
