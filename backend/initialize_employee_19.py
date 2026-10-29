
from sqlalchemy import select, text

from app.db.models.models import Employee
from app.db.session import SessionLocal
from app.services.leave_balance_initializer import (
    initialize_employee_leave_balances,
)


def main():
    with SessionLocal() as db:
        database_name = db.execute(
            text("SELECT current_database()")
        ).scalar_one()

        if database_name != "leave_expense_synthetic":
            raise RuntimeError(
                f"Unsafe database: {database_name}. "
                "Expected leave_expense_synthetic."
            )

        employee = db.scalar(
            select(Employee).where(
                Employee.employee_number == "19"
            )
        )

        if employee is None:
            raise RuntimeError("Employee 19 not found.")

        if employee.country != "IN":
            raise RuntimeError("Employee 19 country mismatch.")

        if str(employee.employment_start_date) != "2026-10-29":
            raise RuntimeError("Employee 19 start date mismatch.")

        try:
            balances = initialize_employee_leave_balances(
                db=db,
                employee=employee,
                year=2026,
            )

            print("Database:", database_name)
            print("Employee:", employee.employee_number)
            print("New balances:", len(balances))

            for balance in balances:
                print(
                    "Policy ID:", balance.leave_policy_id,
                    "| Entitlement:", balance.entitled_days,
                )

            db.commit()
            print("Transaction committed successfully.")

        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    main()
