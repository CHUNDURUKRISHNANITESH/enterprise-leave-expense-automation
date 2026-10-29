
from uuid import uuid4

from app.api.deps import CurrentUser, require_roles
from app.db.models import UserAccount
from app.db.models.models import CostCenter, Employee
from app.db.session import get_db
from app.schemas.employees import (
    EmployeeCreate,
    EmployeeResponse,
    EmployeeUpdate,
)
from app.services.leave_balance_initializer import (
    initialize_employee_leave_balances,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

router = APIRouter(prefix="/employees", tags=["Employees"])


def _validate_references(
    db: Session,
    manager_id: str | None,
    cost_center_id: str | None,
    employee_id: str | None = None,
) -> None:
    if manager_id is not None:
        if manager_id == employee_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An employee cannot be their own manager.",
            )

        manager = db.get(Employee, manager_id)

        if manager is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Manager '{manager_id}' does not exist.",
            )

    if cost_center_id is not None:
        cost_center = db.get(CostCenter, cost_center_id)

        if cost_center is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cost center '{cost_center_id}' does not exist.",
            )


def _check_duplicates(
    db: Session,
    employee_number: str | None = None,
    email: str | None = None,
    exclude_employee_id: str | None = None,
) -> None:
    conditions = []

    if employee_number is not None:
        conditions.append(Employee.employee_number == employee_number)

    if email is not None:
        conditions.append(Employee.email == email)

    if not conditions:
        return

    statement = select(Employee).where(or_(*conditions))

    if exclude_employee_id is not None:
        statement = statement.where(
            Employee.id != exclude_employee_id
        )

    existing = db.scalar(statement)

    if existing is not None:
        if (
            employee_number is not None
            and existing.employee_number == employee_number
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Employee number already exists.",
            )

        if email is not None and existing.email == email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email address already exists.",
            )


@router.get("", response_model=list[EmployeeResponse])
def list_employees(
    current_user: CurrentUser,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    department: str | None = None,
    country: str | None = Query(
        default=None,
        min_length=2,
        max_length=2,
    ),
    search: str | None = Query(
        default=None,
        max_length=150,
    ),
    db: Session = Depends(get_db),
) -> list[Employee]:

    # Regular employees cannot access the directory.
    if current_user.role == "EMPLOYEE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    statement = select(Employee)

    # Managers can only list their direct reports.
    if current_user.role == "MANAGER":
        statement = statement.where(
            Employee.manager_id == current_user.employee_id
        )

    # HR and ADMIN can view all employees.
    if department:
        statement = statement.where(
            Employee.department == department
        )

    if country:
        statement = statement.where(
            Employee.country == country.upper()
        )

    if search and search.strip():
        search_term = search.strip()

        statement = statement.where(
            or_(
                Employee.first_name.ilike(f"%{search_term}%"),
                Employee.last_name.ilike(f"%{search_term}%"),
                Employee.email.ilike(f"%{search_term}%"),
                Employee.employee_number.ilike(f"%{search_term}%"),
            )
        )

    statement = (
        statement
        .order_by(Employee.id)
        .offset(offset)
        .limit(limit)
    )

    return list(db.scalars(statement).all())


@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee(
    employee_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> Employee:

    employee = db.get(Employee, employee_id)

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found.",
        )

    # HR and ADMIN can view all employee profiles.
    if current_user.role in ("HR", "ADMIN"):
        return employee

    # Every authenticated employee can view their own profile.
    if current_user.employee_id == employee_id:
        return employee

    # MANAGER can view employees who report directly to them.
    if (
        current_user.role == "MANAGER"
        and employee.manager_id == current_user.employee_id
    ):
        return employee

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions",
    )


@router.post(
    "",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_employee(
    payload: EmployeeCreate,
    current_user: UserAccount = Depends(
        require_roles("HR", "ADMIN")
    ),
    db: Session = Depends(get_db),
) -> Employee:

    data = payload.model_dump()

    # Validate employment dates.
    if (
        data["employment_end_date"] is not None
        and data["employment_end_date"]
        < data["employment_start_date"]
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Employment end date cannot be before "
                "the start date."
            ),
        )

    # Check duplicate employee number and email.
    _check_duplicates(
        db,
        employee_number=data["employee_number"],
        email=data["email"],
    )

    # Validate manager and cost center.
    _validate_references(
        db,
        manager_id=data["manager_id"],
        cost_center_id=data["cost_center_id"],
    )

    # Create employee record.
    employee = Employee(
        id=f"EMP-{uuid4().hex[:27]}",
        **data,
    )

    db.add(employee)

    try:
        # Initialize leave balances for the new employee.
        initialize_employee_leave_balances(
            db=db,
            employee=employee,
            year=employee.employment_start_date.year,
        )

        db.commit()
        db.refresh(employee)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Employee could not be created because "
                "a unique or database constraint was violated."
            ),
        )

    except Exception:
        db.rollback()
        raise

    return employee


@router.patch(
    "/{employee_id}",
    response_model=EmployeeResponse,
)
def update_employee(
    employee_id: str,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(
        require_roles("HR", "ADMIN")
    ),
) -> Employee:

    employee = db.get(Employee, employee_id)

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found.",
        )

    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one field to update.",
        )

    # Prevent required fields from being set to null.
    for field in (
        "employee_number",
        "first_name",
        "last_name",
        "email",
        "department",
        "country",
        "currency",
        "employment_start_date",
        "employment_status",
        "is_approver",
        "attributes",
    ):
        if field in changes and changes[field] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"'{field}' cannot be null.",
            )

    # Validate updated employment dates.
    start_date = changes.get(
        "employment_start_date",
        employee.employment_start_date,
    )

    end_date = changes.get(
        "employment_end_date",
        employee.employment_end_date,
    )

    if end_date is not None and end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Employment end date cannot be before "
                "the start date."
            ),
        )

    # Check for duplicate employee information.
    _check_duplicates(
        db,
        employee_number=changes.get("employee_number"),
        email=changes.get("email"),
        exclude_employee_id=employee.id,
    )

    # Validate manager and cost center references.
    _validate_references(
        db,
        manager_id=changes.get(
            "manager_id",
            employee.manager_id,
        ),
        cost_center_id=changes.get(
            "cost_center_id",
            employee.cost_center_id,
        ),
        employee_id=employee.id,
    )

    # Apply updated fields.
    for field, value in changes.items():
        setattr(employee, field, value)

    try:
        db.commit()
        db.refresh(employee)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Employee update violated "
                "a database constraint."
            ),
        )

    return employee
