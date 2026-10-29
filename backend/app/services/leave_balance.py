
from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.models import LeaveBalance
from app.services.leave_calculator import calculate_working_days_by_year


def validate_leave_balances(
    db: Session,
    employee_id: str,
    leave_policy_id: str,
    start_date: date,
    end_date: date,
    *,
    lock_for_update: bool = False,
) -> list[tuple[LeaveBalance, Decimal]]:
    """Validate available leave days for every affected calendar year."""

    days_by_year = calculate_working_days_by_year(start_date, end_date)
    validated_balances: list[tuple[LeaveBalance, Decimal]] = []

    for year, working_days in sorted(days_by_year.items()):
        statement = select(LeaveBalance).where(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.leave_policy_id == leave_policy_id,
            LeaveBalance.period_year == year,
        )

        if lock_for_update:
            statement = statement.with_for_update()

        balance = db.scalar(statement)

        if balance is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Leave balance not found for year {year}.",
            )

        required_days = Decimal(working_days)

        if balance.available_days < required_days:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Insufficient leave balance for year {year}. "
                    f"Required: {required_days}, "
                    f"Available: {balance.available_days}."
                ),
            )

        validated_balances.append((balance, required_days))

    return validated_balances


def get_reserved_leave_balances(
    db: Session,
    employee_id: str,
    leave_policy_id: str,
    start_date: date,
    end_date: date,
) -> list[tuple[LeaveBalance, Decimal]]:
    """Retrieve and validate reserved leave days for approval decisions."""

    days_by_year = calculate_working_days_by_year(start_date, end_date)
    reserved_balances: list[tuple[LeaveBalance, Decimal]] = []

    for year, working_days in sorted(days_by_year.items()):
        balance = db.scalar(
            select(LeaveBalance)
            .where(
                LeaveBalance.employee_id == employee_id,
                LeaveBalance.leave_policy_id == leave_policy_id,
                LeaveBalance.period_year == year,
            )
            .with_for_update()
        )

        if balance is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Leave balance not found for year {year}.",
            )

        required_days = Decimal(working_days)

        if balance.pending_days < required_days:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Insufficient reserved leave days for year {year}. "
                    f"Required: {required_days}, "
                    f"Pending: {balance.pending_days}."
                ),
            )

        reserved_balances.append((balance, required_days))

    return reserved_balances

