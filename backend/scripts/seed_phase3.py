
"""Seed minimal Phase 3 integration-test data into PostgreSQL only."""

from datetime import date
from decimal import Decimal
import os

from sqlalchemy import select

from app.core.security import hash_password
from app.db.models import (
    Employee,
    UserAccount,
    CostCenter,
    ExpensePolicy,
    ApprovalRule,
)
from app.db.session import SessionLocal


PASSWORD = os.environ.get("PHASE3_SEED_PASSWORD")
if not PASSWORD:
    raise SystemExit(
        "Set PHASE3_SEED_PASSWORD to a development-only password before running."
    )

EMPLOYEES = [
    ("EMP-P3-ADMIN", "P3-ADMIN", "Phase", "Administrator",
     "phase3.admin@example.com", "ADMIN", None, False),
    ("EMP-P3-MANAGER", "P3-MANAGER", "Phase", "Manager",
     "phase3.manager@example.com", "EMPLOYEE", None, True),
    ("EMP-P3-APPROVER", "P3-APPROVER", "Phase", "Approver",
     "phase3.approver@example.com", "EMPLOYEE", None, True),
    ("EMP-P3-REQUESTER", "P3-REQUESTER", "Phase", "Requester",
     "phase3.requester@example.com", "EMPLOYEE", "EMP-P3-MANAGER", False),
]


def main():
    with SessionLocal() as db:
        if db.bind.dialect.name != "postgresql":
            raise SystemExit("Refusing to seed a non-PostgreSQL database.")

        try:
            # Create employees without manager references first.
            for emp_id, number, first, last, email, role, manager_id, is_approver in EMPLOYEES:
                employee = db.get(Employee, emp_id)
                if employee is None:
                    employee = Employee(
                        id=emp_id,
                        employee_number=number,
                        first_name=first,
                        last_name=last,
                        email=email,
                        department="OPERATIONS",
                        country="IN",
                        currency="INR",
                        employment_start_date=date(2026, 1, 1),
                        employment_status="ACTIVE",
                        is_approver=is_approver,
                        attributes={},
                    )
                    db.add(employee)

            db.flush()

            requester = db.get(Employee, "EMP-P3-REQUESTER")
            requester.manager_id = "EMP-P3-MANAGER"

            for emp_id, number, first, last, email, role, manager_id, is_approver in EMPLOYEES:
                account_id = f"USR-{emp_id}"
                account = db.get(UserAccount, account_id)
                if account is None:
                    db.add(UserAccount(
                        id=account_id,
                        employee_id=emp_id,
                        password_hash=hash_password(PASSWORD),
                        role=role,
                        is_active=True,
                    ))

            if db.get(CostCenter, "CC-P3-001") is None:
                db.add(CostCenter(
                    id="CC-P3-001",
                    code="P3-OPS",
                    name="Phase 3 Operations",
                    country="IN",
                    currency="INR",
                    owner_employee_id="EMP-P3-MANAGER",
                    budget_amount=Decimal("100000.00"),
                    committed_amount=Decimal("0.00"),
                    is_active=True,
                    attributes={},
                ))

            if db.get(ExpensePolicy, "POL-P3-TRAVEL") is None:
                db.add(ExpensePolicy(
                    id="POL-P3-TRAVEL",
                    policy_code="P3-TRAVEL",
                    name="Phase 3 Travel Policy",
                    country="IN",
                    category="TRAVEL",
                    currency="INR",
                    per_item_limit=Decimal("10000.00"),
                    max_amount=Decimal("20000.00"),
                    min_receipt_amount=Decimal("1.00"),
                    receipt_required=True,
                    requires_business_purpose=True,
                    effective_from=date(2026, 1, 1),
                    version=1,
                    rules={},
                ))

            rules = [
                (
                    "RULE-P3-MANAGER",
                    "Phase 3 Manager Approval",
                    "MANAGER",
                    None,
                    1,
                ),
                (
                    "RULE-P3-SECOND",
                    "Phase 3 Second Approval",
                    "EMPLOYEE",
                    "EMP-P3-APPROVER",
                    2,
                ),
            ]

            for rule_id, name, approver_type, approver_id, level in rules:
                if db.get(ApprovalRule, rule_id) is None:
                    db.add(ApprovalRule(
                        id=rule_id,
                        name=name,
                        country="IN",
                        category="TRAVEL",
                        currency="INR",
                        min_amount=Decimal("0.00"),
                        max_amount=None,
                        approver_type=approver_type,
                        approver_employee_id=approver_id,
                        approval_level=level,
                        effective_from=date(2026, 1, 1),
                        priority=10,
                        is_active=True,
                        conditions={},
                    ))

            db.commit()
            print("Phase 3 PostgreSQL development seed completed.")
            print("Requester: phase3.requester@example.com")
            print("Manager: phase3.manager@example.com")
            print("Second approver: phase3.approver@example.com")
            print("Admin: phase3.admin@example.com")
            print("Password: value from PHASE3_SEED_PASSWORD")

        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    main()
