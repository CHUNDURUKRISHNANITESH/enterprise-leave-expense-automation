
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.models import Employee, LeaveBalance, LeavePolicy


def calculate_prorated_entitlement(
    annual_entitlement: Decimal,
    employment_start_date: date,
    year: int,
    policy_effective_from: date,
    policy_effective_to: date | None = None,
    employment_end_date: date | None = None,
) -> Decimal:
    """Calculate calendar-day-prorated leave entitlement."""

    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)

    eligible_start = max(
        year_start,
        employment_start_date,
        policy_effective_from,
    )

    eligible_end = min(
        year_end,
        policy_effective_to or year_end,
        employment_end_date or year_end,
    )

    if eligible_start > eligible_end:
        return Decimal("0.00")

    eligible_days = (eligible_end - eligible_start).days + 1
    total_days = (year_end - year_start).days + 1

    entitlement = (
        Decimal(str(annual_entitlement))
        * Decimal(eligible_days)
        / Decimal(total_days)
    )

    return entitlement.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def initialize_employee_leave_balances(
    db: Session,
    employee: Employee,
    year: int,
) -> list[LeaveBalance]:
    """
    Initialize applicable leave balances without overwriting existing records.

    The caller is responsible for committing the database transaction.
    """

    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)

    policies = db.scalars(
        select(LeavePolicy).where(
            LeavePolicy.country == employee.country,
            LeavePolicy.effective_from <= year_end,
            (
                (LeavePolicy.effective_to.is_(None))
                | (LeavePolicy.effective_to >= year_start)
            ),
        )
    ).all()

    existing_policy_ids = set(
        db.scalars(
            select(LeaveBalance.leave_policy_id).where(
                LeaveBalance.employee_id == employee.id,
                LeaveBalance.period_year == year,
            )
        ).all()
    )

    created_balances = []

    for policy in policies:
        if policy.id in existing_policy_ids:
            continue

        # This service currently supports annual entitlement policies.
        if policy.accrual_frequency != "ANNUAL":
            continue

        entitlement = calculate_prorated_entitlement(
            annual_entitlement=policy.annual_entitlement,
            employment_start_date=employee.employment_start_date,
            year=year,
            policy_effective_from=policy.effective_from,
            policy_effective_to=policy.effective_to,
            employment_end_date=employee.employment_end_date,
        )

        if entitlement <= 0:
            continue

        balance = LeaveBalance(
            id=f"LB-{uuid4().hex[:27]}",
            employee_id=employee.id,
            leave_policy_id=policy.id,
            period_year=year,
            entitled_days=entitlement,
            used_days=Decimal("0.00"),
            pending_days=Decimal("0.00"),
            carryover_days=Decimal("0.00"),
            adjustment_days=Decimal("0.00"),
            last_calculated_at=datetime.now(UTC),
            notes="Initial calendar-day-prorated entitlement",
        )

        db.add(balance)
        created_balances.append(balance)
        existing_policy_ids.add(policy.id)

    return created_balances
