
import uuid
from getpass import getpass

from sqlalchemy import select
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.core.security import hash_password
from app.db.models import Employee, UserAccount
from app.db.session import SessionLocal


database_name = make_url(settings.database_url).database

if database_name != "leave_expense_synthetic":
    raise SystemExit("Incorrect database. Operation cancelled.")

password = getpass("Enter test admin password: ")

if len(password) < 12:
    raise SystemExit("Password must contain at least 12 characters.")

with SessionLocal() as db:
    employee = db.scalar(
        select(Employee)
        .where(Employee.employment_status == "ACTIVE")
        .where(
            ~Employee.id.in_(
                select(UserAccount.employee_id)
            )
        )
        .order_by(Employee.id)
        .limit(1)
    )

    if employee is None:
        raise SystemExit("No eligible employee found.")

    account = UserAccount(
        id=f"USR-{uuid.uuid4().hex[:24]}",
        employee_id=employee.id,
        password_hash=hash_password(password),
        role="ADMIN",
        is_active=True,
    )

    db.add(account)
    db.commit()

    print("ADMIN account created successfully.")
    print("Employee ID:", employee.id)
    print("Login email:", employee.email)
    print("Role:", account.role)
