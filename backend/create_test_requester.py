
from getpass import getpass
from uuid import uuid4

from sqlalchemy import select

from app.core.security import hash_password
from app.db.models.models import Employee, UserAccount
from app.db.session import SessionLocal

EMPLOYEE_ID = "EMP-000002"

with SessionLocal() as db:
    if db.bind.dialect.name != "postgresql":
        raise SystemExit("Expected PostgreSQL database.")

    database_name = db.execute(
        __import__("sqlalchemy").text("SELECT current_database()")
    ).scalar_one()

    if database_name != "leave_expense_synthetic":
        raise SystemExit(
            f"Safety check failed: connected to {database_name}"
        )

    employee = db.get(Employee, EMPLOYEE_ID)

    if employee is None or employee.employment_status != "ACTIVE":
        raise SystemExit("Requester employee is missing or inactive.")

    existing = db.scalar(
        select(UserAccount).where(
            UserAccount.employee_id == EMPLOYEE_ID
        )
    )

    if existing:
        raise SystemExit("Requester account already exists.")

    password = getpass("Create requester password: ")
    confirmation = getpass("Confirm requester password: ")

    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    if len(password) < 12:
        raise SystemExit("Password must contain at least 12 characters.")

    employee.email = "generated.employee.000002@example.com"

    account = UserAccount(
        id=f"USR-TEST-{uuid4().hex[:12]}",
        employee_id=EMPLOYEE_ID,
        password_hash=hash_password(password),
        role="EMPLOYEE",
        is_active=True,
    )

    db.add(account)
    db.commit()

    print("\nRequester account created successfully.")
    print("Employee ID:", EMPLOYEE_ID)
    print("Login email:", employee.email)
    print("Role: EMPLOYEE")
    print("Database:", database_name)
