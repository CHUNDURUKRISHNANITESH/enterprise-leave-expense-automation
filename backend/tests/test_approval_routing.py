
import pytest
from fastapi import HTTPException

from app.db.models.models import Employee
from app.services.approval_routing import validate_approver


def make_approver(db_session, **overrides):
    """Create an employee for approval validation tests."""
    from uuid import uuid4
    from datetime import date

    employee_id = f"EMP-{uuid4().hex[:27]}"

    data = {
        "id": employee_id,
        "employee_number": f"E-{uuid4().hex[:10]}",
        "first_name": "Test",
        "last_name": "Approver",
        "email": f"{uuid4().hex[:12]}@example.com",
        "department": "HR",
        "country": "IN",
        "currency": "INR",
        "employment_start_date": date(2025, 1, 1),
        "employment_status": "ACTIVE",
        "is_approver": True,
        "attributes": {"approval_roles": ["HR"]},
    }

    data.update(overrides)

    employee = Employee(**data)
    db_session.add(employee)
    db_session.commit()

    return employee


def test_validate_active_approver(db_session):
    approver = make_approver(db_session)

    result = validate_approver(
        db_session,
        approver_employee_id=approver.id,
        requester_employee_id="EMP-REQUESTER",
    )

    assert result.id == approver.id


def test_reject_self_approval(db_session):
    approver = make_approver(db_session)

    with pytest.raises(HTTPException) as exc:
        validate_approver(
            db_session,
            approver_employee_id=approver.id,
            requester_employee_id=approver.id,
        )

    assert exc.value.status_code == 400
    assert "own request" in exc.value.detail


def test_reject_missing_approver(db_session):
    with pytest.raises(HTTPException) as exc:
        validate_approver(
            db_session,
            approver_employee_id="EMP-MISSING",
            requester_employee_id="EMP-REQUESTER",
        )

    assert exc.value.status_code == 400


def test_reject_inactive_approver(db_session):
    approver = make_approver(
        db_session,
        employment_status="INACTIVE",
    )

    with pytest.raises(HTTPException) as exc:
        validate_approver(
            db_session,
            approver_employee_id=approver.id,
            requester_employee_id="EMP-REQUESTER",
        )

    assert exc.value.status_code == 400
    assert "not an active employee" in exc.value.detail


def test_reject_approver_without_authority(db_session):
    approver = make_approver(
        db_session,
        is_approver=False,
    )

    with pytest.raises(HTTPException) as exc:
        validate_approver(
            db_session,
            approver_employee_id=approver.id,
            requester_employee_id="EMP-REQUESTER",
        )

    assert exc.value.status_code == 400
    assert "approval authority" in exc.value.detail


def test_resolve_valid_manager_approver(db_session):
    from app.services.approval_routing import resolve_manager_approver

    manager = make_approver(db_session)
    requester = make_approver(
        db_session,
        manager_id=manager.id,
        is_approver=False,
    )

    result = resolve_manager_approver(
        db_session,
        requester_employee_id=requester.id,
    )

    assert result.id == manager.id


def test_reject_requester_without_manager(db_session):
    from app.services.approval_routing import resolve_manager_approver

    requester = make_approver(
        db_session,
        is_approver=False,
    )

    with pytest.raises(HTTPException) as exc:
        resolve_manager_approver(
            db_session,
            requester_employee_id=requester.id,
        )

    assert exc.value.status_code == 400
    assert "reporting manager" in exc.value.detail


def test_reject_manager_without_approval_authority(db_session):
    from app.services.approval_routing import resolve_manager_approver

    manager = make_approver(
        db_session,
        is_approver=False,
    )

    requester = make_approver(
        db_session,
        manager_id=manager.id,
        is_approver=False,
    )

    with pytest.raises(HTTPException) as exc:
        resolve_manager_approver(
            db_session,
            requester_employee_id=requester.id,
        )

    assert exc.value.status_code == 400
    assert "approval authority" in exc.value.detail


def test_reject_missing_requester_in_manager_routing(db_session):
    from app.services.approval_routing import resolve_manager_approver

    with pytest.raises(HTTPException) as exc:
        resolve_manager_approver(
            db_session,
            requester_employee_id="EMP-NOT-FOUND",
        )

    assert exc.value.status_code == 400
    assert "Requester employee does not exist" in exc.value.detail


def test_resolve_valid_explicit_approver(db_session):
    from app.services.approval_routing import resolve_explicit_approver

    approver = make_approver(db_session)

    result = resolve_explicit_approver(
        db_session,
        requester_employee_id="EMP-REQUESTER",
        approver_employee_id=approver.id,
    )

    assert result.id == approver.id


def test_reject_explicit_approver_not_configured(db_session):
    from app.services.approval_routing import resolve_explicit_approver

    with pytest.raises(HTTPException) as exc:
        resolve_explicit_approver(
            db_session,
            requester_employee_id="EMP-REQUESTER",
            approver_employee_id=None,
        )

    assert exc.value.status_code == 400
    assert "does not specify an approver employee" in exc.value.detail


def test_reject_explicit_self_approval(db_session):
    from app.services.approval_routing import resolve_explicit_approver

    approver = make_approver(db_session)

    with pytest.raises(HTTPException) as exc:
        resolve_explicit_approver(
            db_session,
            requester_employee_id=approver.id,
            approver_employee_id=approver.id,
        )

    assert exc.value.status_code == 400
    assert "own request" in exc.value.detail


def test_reject_inactive_explicit_approver(db_session):
    from app.services.approval_routing import resolve_explicit_approver

    approver = make_approver(
        db_session,
        employment_status="INACTIVE",
    )

    with pytest.raises(HTTPException) as exc:
        resolve_explicit_approver(
            db_session,
            requester_employee_id="EMP-REQUESTER",
            approver_employee_id=approver.id,
        )

    assert exc.value.status_code == 400
    assert "not an active employee" in exc.value.detail


def test_resolve_valid_role_approver(db_session):
    from app.services.approval_routing import resolve_role_approver

    approver = make_approver(
        db_session,
        attributes={"approval_roles": ["HR", "FINANCE"]},
    )

    result = resolve_role_approver(
        db_session,
        requester_employee_id="EMP-REQUESTER",
        approver_role="HR",
    )

    assert result.id == approver.id


def test_reject_missing_approval_role(db_session):
    from app.services.approval_routing import resolve_role_approver

    with pytest.raises(HTTPException) as exc:
        resolve_role_approver(
            db_session,
            requester_employee_id="EMP-REQUESTER",
            approver_role=None,
        )

    assert exc.value.status_code == 400
    assert "does not specify an approver role" in exc.value.detail


def test_reject_inactive_role_approver(db_session):
    from app.services.approval_routing import resolve_role_approver

    make_approver(
        db_session,
        employment_status="INACTIVE",
        attributes={"approval_roles": ["HR"]},
    )

    with pytest.raises(HTTPException) as exc:
        resolve_role_approver(
            db_session,
            requester_employee_id="EMP-REQUESTER",
            approver_role="HR",
        )

    assert exc.value.status_code == 400
    assert "No eligible approver" in exc.value.detail


def test_reject_role_based_self_approval(db_session):
    from app.services.approval_routing import resolve_role_approver

    requester = make_approver(
        db_session,
        attributes={"approval_roles": ["HR"]},
    )

    with pytest.raises(HTTPException) as exc:
        resolve_role_approver(
            db_session,
            requester_employee_id=requester.id,
            approver_role="HR",
        )

    assert exc.value.status_code == 400
    assert "No eligible approver" in exc.value.detail


def test_reject_invalid_approval_roles_format(db_session):
    from app.services.approval_routing import resolve_role_approver

    make_approver(
        db_session,
        attributes={"approval_roles": "HR"},
    )

    with pytest.raises(HTTPException) as exc:
        resolve_role_approver(
            db_session,
            requester_employee_id="EMP-REQUESTER",
            approver_role="HR",
        )

    assert exc.value.status_code == 400
    assert "No eligible approver" in exc.value.detail


def test_reject_ambiguous_role_approvers(db_session):
    from app.services.approval_routing import resolve_role_approver

    make_approver(
        db_session,
        attributes={"approval_roles": ["HR"]},
    )

    make_approver(
        db_session,
        attributes={"approval_roles": ["HR"]},
    )

    with pytest.raises(HTTPException) as exc:
        resolve_role_approver(
            db_session,
            requester_employee_id="EMP-REQUESTER",
            approver_role="HR",
        )

    assert exc.value.status_code == 409
    assert "Multiple eligible approvers" in exc.value.detail


def test_find_matching_country_leave_rule(db_session):
    from datetime import date
    from app.db.models.models import ApprovalRule
    from app.services.approval_routing import find_matching_leave_rules

    rule = ApprovalRule(
        id="RULE-IN-LEAVE-1",
        name="India Leave Manager Approval",
        country="IN",
        category="LEAVE",
        min_amount=0,
        approver_type="MANAGER",
        approval_level=1,
        effective_from=date(2026, 1, 1),
        priority=100,
        is_active=True,
        conditions={},
    )
    db_session.add(rule)
    db_session.commit()

    result = find_matching_leave_rules(
        db_session,
        country="IN",
        as_of_date=date(2026, 10, 28),
    )

    assert len(result) == 1
    assert result[0].id == rule.id


def test_find_matching_multi_level_leave_rules(db_session):
    from datetime import date
    from app.db.models.models import ApprovalRule
    from app.services.approval_routing import find_matching_leave_rules

    for level, approver_type in [
        (3, "ROLE"),
        (1, "MANAGER"),
        (2, "EMPLOYEE"),
    ]:
        db_session.add(
            ApprovalRule(
                id=f"RULE-LEVEL-{level}",
                name=f"Approval Level {level}",
                country="IN",
                category="LEAVE",
                min_amount=0,
                approver_type=approver_type,
                approval_level=level,
                effective_from=date(2026, 1, 1),
                priority=100,
                is_active=True,
                conditions={},
            )
        )

    db_session.commit()

    result = find_matching_leave_rules(
        db_session,
        country="IN",
        as_of_date=date(2026, 10, 28),
    )

    assert [rule.approval_level for rule in result] == [1, 2, 3]


def test_reject_when_no_matching_leave_rules(db_session):
    from datetime import date
    from app.services.approval_routing import find_matching_leave_rules

    with pytest.raises(HTTPException) as exc:
        find_matching_leave_rules(
            db_session,
            country="IN",
            as_of_date=date(2026, 10, 28),
        )

    assert exc.value.status_code == 400
    assert "No applicable leave approval rules" in exc.value.detail



def test_country_specific_rule_overrides_global_rule(db_session):
    from datetime import date
    from app.db.models.models import ApprovalRule
    from app.services.approval_routing import find_matching_leave_rules

    global_rule = ApprovalRule(
        id="RULE-GLOBAL-LEAVE",
        name="Global Leave Approval",
        country=None,
        category="LEAVE",
        min_amount=0,
        approver_type="MANAGER",
        approval_level=1,
        effective_from=date(2026, 1, 1),
        priority=1,
        is_active=True,
        conditions={},
    )

    india_rule = ApprovalRule(
        id="RULE-INDIA-LEAVE",
        name="India Leave Approval",
        country="IN",
        category="LEAVE",
        min_amount=0,
        approver_type="ROLE",
        approver_role="HR",
        approval_level=1,
        effective_from=date(2026, 1, 1),
        priority=100,
        is_active=True,
        conditions={},
    )

    db_session.add_all([global_rule, india_rule])
    db_session.commit()

    result = find_matching_leave_rules(
        db_session,
        country="IN",
        as_of_date=date(2026, 10, 28),
    )

    assert len(result) == 1
    assert result[0].id == "RULE-INDIA-LEAVE"


def test_lower_priority_number_wins(db_session):
    from datetime import date
    from app.db.models.models import ApprovalRule
    from app.services.approval_routing import find_matching_leave_rules

    manager_rule = ApprovalRule(
        id="RULE-MANAGER-PRIORITY",
        name="Manager Approval",
        country="IN",
        category="LEAVE",
        min_amount=0,
        approver_type="MANAGER",
        approval_level=1,
        effective_from=date(2026, 1, 1),
        priority=100,
        is_active=True,
        conditions={},
    )

    hr_rule = ApprovalRule(
        id="RULE-HR-PRIORITY",
        name="HR Approval",
        country="IN",
        category="LEAVE",
        min_amount=0,
        approver_type="ROLE",
        approver_role="HR",
        approval_level=1,
        effective_from=date(2026, 1, 1),
        priority=10,
        is_active=True,
        conditions={},
    )

    db_session.add_all([manager_rule, hr_rule])
    db_session.commit()

    result = find_matching_leave_rules(
        db_session,
        country="IN",
        as_of_date=date(2026, 10, 28),
    )

    assert len(result) == 1
    assert result[0].id == "RULE-HR-PRIORITY"


def test_reject_ambiguous_approval_rules(db_session):
    from datetime import date

    from app.db.models.models import ApprovalRule
    from app.services.approval_routing import find_matching_leave_rules

    for rule_id, approver_type in [
        ("RULE-AMBIGUOUS-MANAGER", "MANAGER"),
        ("RULE-AMBIGUOUS-HR", "ROLE"),
    ]:
        db_session.add(
            ApprovalRule(
                id=rule_id,
                name=f"Approval {rule_id}",
                country="IN",
                category="LEAVE",
                min_amount=0,
                approver_type=approver_type,
                approver_role="HR" if approver_type == "ROLE" else None,
                approval_level=1,
                effective_from=date(2026, 1, 1),
                priority=100,
                is_active=True,
                conditions={},
            )
        )

    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        find_matching_leave_rules(
            db_session,
            country="IN",
            as_of_date=date(2026, 10, 28),
        )

    assert exc.value.status_code == 409
    assert "Ambiguous approval rules at level 1" in exc.value.detail


def test_leave_rules_respect_effective_dates_and_active_status(db_session):
    from datetime import date

    from app.db.models.models import ApprovalRule
    from app.services.approval_routing import find_matching_leave_rules

    configurations = [
        ("RULE-EXPIRED", date(2026, 1, 1), date(2026, 6, 30), True),
        ("RULE-FUTURE", date(2027, 1, 1), None, True),
        ("RULE-CURRENT", date(2026, 1, 1), date(2026, 12, 31), True),
        ("RULE-INACTIVE", date(2026, 1, 1), date(2026, 12, 31), False),
    ]

    for rule_id, effective_from, effective_to, is_active in configurations:
        db_session.add(
            ApprovalRule(
                id=rule_id,
                name=rule_id,
                country="IN",
                category="LEAVE",
                min_amount=0,
                approver_type="MANAGER",
                approval_level=1,
                effective_from=effective_from,
                effective_to=effective_to,
                priority=100,
                is_active=is_active,
                conditions={},
            )
        )

    db_session.commit()

    result = find_matching_leave_rules(
        db_session,
        country="IN",
        as_of_date=date(2026, 10, 28),
    )

    assert len(result) == 1
    assert result[0].id == "RULE-CURRENT"


def test_reject_unsupported_leave_rule_conditions(db_session):
    from datetime import date

    from app.db.models.models import ApprovalRule
    from app.services.approval_routing import find_matching_leave_rules

    rule = ApprovalRule(
        id="RULE-UNSUPPORTED-CONDITION",
        name="Conditional Leave Approval",
        country="IN",
        category="LEAVE",
        min_amount=0,
        approver_type="MANAGER",
        approval_level=1,
        effective_from=date(2026, 1, 1),
        priority=100,
        is_active=True,
        conditions={"minimum_leave_days": 5},
    )

    db_session.add(rule)
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        find_matching_leave_rules(
            db_session,
            country="IN",
            as_of_date=date(2026, 10, 28),
        )

    assert exc.value.status_code == 400
    assert "conditions that are not supported yet" in exc.value.detail


def test_expense_specific_rules_excluded_from_leave_routing(db_session):
    from datetime import date
    from decimal import Decimal

    from app.db.models.models import ApprovalRule
    from app.services.approval_routing import find_matching_leave_rules

    expense_rule = ApprovalRule(
        id="RULE-EXPENSE-ONLY",
        name="Expense Approval",
        country="IN",
        category="EXPENSE",
        min_amount=Decimal("10000.00"),
        currency="INR",
        approver_type="MANAGER",
        approval_level=1,
        effective_from=date(2026, 1, 1),
        priority=1,
        is_active=True,
        conditions={},
    )

    leave_rule = ApprovalRule(
        id="RULE-LEAVE-ONLY",
        name="Leave Approval",
        country="IN",
        category="LEAVE",
        min_amount=Decimal("0.00"),
        approver_type="MANAGER",
        approval_level=1,
        effective_from=date(2026, 1, 1),
        priority=100,
        is_active=True,
        conditions={},
    )

    db_session.add_all([expense_rule, leave_rule])
    db_session.commit()

    result = find_matching_leave_rules(
        db_session,
        country="IN",
        as_of_date=date(2026, 10, 28),
    )

    assert len(result) == 1
    assert result[0].id == "RULE-LEAVE-ONLY"



def test_generic_expense_threshold_rules_excluded_from_leave_routing(db_session):
    from datetime import date
    from decimal import Decimal

    from app.db.models.models import ApprovalRule
    from app.services.approval_routing import find_matching_leave_rules

    generic_expense_rule = ApprovalRule(
        id="RULE-GENERIC-EXPENSE",
        name="Generic Expense Threshold Approval",
        country="IN",
        category=None,
        min_amount=Decimal("10000.00"),
        currency="INR",
        approver_type="MANAGER",
        approval_level=1,
        effective_from=date(2026, 1, 1),
        priority=1,
        is_active=True,
        conditions={},
    )

    valid_leave_rule = ApprovalRule(
        id="RULE-VALID-LEAVE",
        name="Valid Leave Approval",
        country="IN",
        category="LEAVE",
        min_amount=Decimal("0.00"),
        approver_type="MANAGER",
        approval_level=1,
        effective_from=date(2026, 1, 1),
        priority=100,
        is_active=True,
        conditions={},
    )

    db_session.add_all([generic_expense_rule, valid_leave_rule])
    db_session.commit()

    result = find_matching_leave_rules(
        db_session,
        country="IN",
        as_of_date=date(2026, 10, 28),
    )

    assert len(result) == 1
    assert result[0].id == "RULE-VALID-LEAVE"


def test_create_single_manager_leave_approval_step(db_session):
    from datetime import date

    from app.db.models.models import (
        ApprovalRule,
        ApprovalStep,
        LeaveRequest,
        LeavePolicy,
    )
    from app.services.approval_routing import create_leave_approval_steps

    manager = make_approver(db_session)

    requester = make_approver(
        db_session,
        manager_id=manager.id,
        is_approver=False,
    )

    policy = LeavePolicy(
        id="LP-TEST-APPROVAL",
        policy_code="ANNUAL-IN-APPROVAL-TEST",
        name="Test Approval Leave Policy",
        country="IN",
        leave_type="ANNUAL",
        annual_entitlement=20,
        effective_from=date(2026, 1, 1),
    )


    db_session.add(policy)
    db_session.flush()

    leave_request = LeaveRequest(
        id="LR-TEST-APPROVAL",
        employee_id=requester.id,
        leave_policy_id=policy.id,
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 11),
        requested_days=2,
        status="SUBMITTED",
    )

    rule = ApprovalRule(
        id="RULE-TEST-MANAGER",
        name="Manager Leave Approval",
        country="IN",
        category="LEAVE",
        min_amount=0,
        approver_type="MANAGER",
        approval_level=1,
        effective_from=date(2026, 1, 1),
        priority=100,
        is_active=True,
        conditions={},
    )

    db_session.add_all([leave_request, rule])
    db_session.commit()

    steps = create_leave_approval_steps(
        db_session,
        leave_request=leave_request,
        as_of_date=date(2026, 10, 28),
    )

    db_session.flush()

    assert len(steps) == 1
    assert steps[0].step_number == 1
    assert steps[0].approver_employee_id == manager.id
    assert steps[0].status == "PENDING"
    assert steps[0].leave_request_id == leave_request.id
    assert steps[0].rule_id == rule.id

    saved_steps = (
        db_session.query(ApprovalStep)
        .filter(ApprovalStep.leave_request_id == leave_request.id)
        .all()
    )

    assert len(saved_steps) == 1


def test_create_multi_level_leave_approval_steps(db_session):
    from datetime import date

    from app.db.models.models import (
        ApprovalRule,
        LeavePolicy,
        LeaveRequest,
    )
    from app.services.approval_routing import create_leave_approval_steps

    manager = make_approver(db_session)
    
    hr_approver = make_approver(
        db_session,
        attributes={"approval_roles": ["HR"]},
    )

    requester = make_approver(
        db_session,
        manager_id=manager.id,
        is_approver=False,
        attributes={},
    )

    policy = LeavePolicy(
        id="LP-MULTI-LEVEL",
        policy_code="MULTI-LEVEL-IN",
        name="Multi Level Leave Policy",
        country="IN",
        leave_type="ANNUAL",
        annual_entitlement=20,
        effective_from=date(2026, 1, 1),
    )

    db_session.add(policy)
    db_session.flush()

    leave_request = LeaveRequest(
        id="LR-MULTI-LEVEL",
        employee_id=requester.id,
        leave_policy_id=policy.id,
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 11),
        requested_days=2,
        status="SUBMITTED",
    )

    manager_rule = ApprovalRule(
        id="RULE-MULTI-MANAGER",
        name="Manager Approval",
        country="IN",
        category="LEAVE",
        min_amount=0,
        approver_type="MANAGER",
        approval_level=1,
        effective_from=date(2026, 1, 1),
        priority=100,
        is_active=True,
        conditions={},
    )

    hr_rule = ApprovalRule(
        id="RULE-MULTI-HR",
        name="HR Approval",
        country="IN",
        category="LEAVE",
        min_amount=0,
        approver_type="ROLE",
        approver_role="HR",
        approval_level=2,
        effective_from=date(2026, 1, 1),
        priority=100,
        is_active=True,
        conditions={},
    )

    db_session.add_all([leave_request, manager_rule, hr_rule])
    db_session.commit()

    steps = create_leave_approval_steps(
        db_session,
        leave_request=leave_request,
        as_of_date=date(2026, 10, 28),
    )

    db_session.flush()

    assert len(steps) == 2

    assert steps[0].step_number == 1
    assert steps[0].approver_employee_id == manager.id
    assert steps[0].rule_id == manager_rule.id

    assert steps[1].step_number == 2
    assert steps[1].approver_employee_id == hr_approver.id
    assert steps[1].rule_id == hr_rule.id

    assert all(step.status == "PENDING" for step in steps)
    assert all(step.leave_request_id == leave_request.id for step in steps)


def test_create_multi_level_leave_approval_steps(db_session):
    from datetime import date

    from app.db.models.models import (
        ApprovalRule,
        LeavePolicy,
        LeaveRequest,
    )
    from app.services.approval_routing import create_leave_approval_steps
 
    manager = make_approver(
        db_session,
        attributes={"approval_roles": ["MANAGER"]},
    )


    hr_approver = make_approver(
        db_session,
        attributes={"approval_roles": ["HR"]},
    )

    requester = make_approver(
        db_session,
        manager_id=manager.id,
        is_approver=False,
        attributes={},
    )

    policy = LeavePolicy(
        id="LP-MULTI-LEVEL",
        policy_code="MULTI-LEVEL-IN",
        name="Multi Level Leave Policy",
        country="IN",
        leave_type="ANNUAL",
        annual_entitlement=20,
        effective_from=date(2026, 1, 1),
    )

    db_session.add(policy)
    db_session.flush()

    leave_request = LeaveRequest(
        id="LR-MULTI-LEVEL",
        employee_id=requester.id,
        leave_policy_id=policy.id,
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 11),
        requested_days=2,
        status="SUBMITTED",
    )

    manager_rule = ApprovalRule(
        id="RULE-MULTI-MANAGER",
        name="Manager Approval",
        country="IN",
        category="LEAVE",
        min_amount=0,
        approver_type="MANAGER",
        approval_level=1,
        effective_from=date(2026, 1, 1),
        priority=100,
        is_active=True,
        conditions={},
    )

    hr_rule = ApprovalRule(
        id="RULE-MULTI-HR",
        name="HR Approval",
        country="IN",
        category="LEAVE",
        min_amount=0,
        approver_type="ROLE",
        approver_role="HR",
        approval_level=2,
        effective_from=date(2026, 1, 1),
        priority=100,
        is_active=True,
        conditions={},
    )

    db_session.add_all([leave_request, manager_rule, hr_rule])
    db_session.commit()

    steps = create_leave_approval_steps(
        db_session,
        leave_request=leave_request,
        as_of_date=date(2026, 10, 28),
    )

    db_session.flush()

    assert len(steps) == 2

    assert steps[0].step_number == 1
    assert steps[0].approver_employee_id == manager.id
    assert steps[0].rule_id == manager_rule.id

    assert steps[1].step_number == 2
    assert steps[1].approver_employee_id == hr_approver.id
    assert steps[1].rule_id == hr_rule.id

    assert all(step.status == "PENDING" for step in steps)
    assert all(step.leave_request_id == leave_request.id for step in steps)


def test_prevent_duplicate_leave_approval_steps(db_session):
    from datetime import date

    from app.db.models.models import (
        ApprovalRule,
        ApprovalStep,
        LeavePolicy,
        LeaveRequest,
    )
    from app.services.approval_routing import create_leave_approval_steps

    manager = make_approver(
        db_session,
        attributes={"approval_roles": ["MANAGER"]},
    )

    requester = make_approver(
        db_session,
        manager_id=manager.id,
        is_approver=False,
        attributes={},
    )

    policy = LeavePolicy(
        id="LP-DUPLICATE-TEST",
        policy_code="DUPLICATE-TEST-IN",
        name="Duplicate Prevention Leave Policy",
        country="IN",
        leave_type="ANNUAL",
        annual_entitlement=20,
        effective_from=date(2026, 1, 1),
    )

    leave_request = LeaveRequest(
        id="LR-DUPLICATE-TEST",
        employee_id=requester.id,
        leave_policy_id=policy.id,
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 11),
        requested_days=2,
        status="SUBMITTED",
    )

    rule = ApprovalRule(
        id="RULE-DUPLICATE-TEST",
        name="Manager Approval",
        country="IN",
        category="LEAVE",
        min_amount=0,
        approver_type="MANAGER",
        approval_level=1,
        effective_from=date(2026, 1, 1),
        priority=100,
        is_active=True,
        conditions={},
    )

    db_session.add_all([policy, leave_request, rule])
    db_session.commit()

    first_steps = create_leave_approval_steps(
        db_session,
        leave_request=leave_request,
        as_of_date=date(2026, 10, 28),
    )

    db_session.flush()

    assert len(first_steps) == 1

    with pytest.raises(HTTPException) as exc:
        create_leave_approval_steps(
            db_session,
            leave_request=leave_request,
            as_of_date=date(2026, 10, 28),
        )

    assert exc.value.status_code == 409
    assert "Approval steps already exist" in exc.value.detail

    saved_steps = (
        db_session.query(ApprovalStep)
        .filter(ApprovalStep.leave_request_id == leave_request.id)
        .all()
    )

    assert len(saved_steps) == 1



def test_leave_approval_steps_rollback(db_session):
    from datetime import date
    from sqlalchemy import select

    from app.db.models.models import (
        ApprovalRule,
        ApprovalStep,
        LeavePolicy,
        LeaveRequest,
    )
    from app.services.approval_routing import create_leave_approval_steps

    manager = make_approver(
        db_session,
        attributes={"approval_roles": ["MANAGER"]},
    )

    requester = make_approver(
        db_session,
        manager_id=manager.id,
        is_approver=False,
        attributes={},
    )

    policy = LeavePolicy(
        id="LP-ROLLBACK-TEST",
        policy_code="ROLLBACK-TEST-IN",
        name="Rollback Test Leave Policy",
        country="IN",
        leave_type="ANNUAL",
        annual_entitlement=20,
        effective_from=date(2026, 1, 1),
    )

    leave_request = LeaveRequest(
        id="LR-ROLLBACK-TEST",
        employee_id=requester.id,
        leave_policy_id=policy.id,
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 11),
        requested_days=2,
        status="SUBMITTED",
    )

    rule = ApprovalRule(
        id="RULE-ROLLBACK-TEST",
        name="Manager Approval",
        country="IN",
        category="LEAVE",
        min_amount=0,
        approver_type="MANAGER",
        approval_level=1,
        effective_from=date(2026, 1, 1),
        priority=100,
        is_active=True,
        conditions={},
    )

    db_session.add_all([policy, leave_request, rule])
    db_session.commit()

    steps = create_leave_approval_steps(
        db_session,
        leave_request=leave_request,
        as_of_date=date(2026, 10, 28),
    )

    db_session.flush()

    assert len(steps) == 1

    # Simulate an API failure before committing approval steps.
    db_session.rollback()

    saved_steps = db_session.scalars(
        select(ApprovalStep).where(
            ApprovalStep.leave_request_id == leave_request.id
        )
    ).all()

    assert saved_steps == []

    # Previously committed records must remain intact.
    assert db_session.get(LeaveRequest, leave_request.id) is not None






