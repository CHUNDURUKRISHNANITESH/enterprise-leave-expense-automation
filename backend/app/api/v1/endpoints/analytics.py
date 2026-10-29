
from decimal import Decimal
from pathlib import Path

from app.api.deps import require_roles
from app.db.session import get_db
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
    dependencies=[Depends(require_roles("ADMIN"))],
)

SQL_DIR = Path(__file__).resolve().parents[4] / "sql" / "analytics"


def run_analytics_query(db: Session, filename: str):
    sql_path = SQL_DIR / filename
    sql_query = sql_path.read_text(encoding="utf-8-sig")

    rows = db.execute(text(sql_query)).mappings().all()

    return [
        {
            key: str(value) if isinstance(value, Decimal) else value
            for key, value in row.items()
        }
        for row in rows
    ]


@router.get("/leave-utilization")
def leave_utilization(db: Session = Depends(get_db)):
    return run_analytics_query(
        db,
        "01_leave_utilization.sql",
    )


@router.get("/expenses")
def expense_analytics(db: Session = Depends(get_db)):
    return run_analytics_query(
        db,
        "02_expense_analytics.sql",
    )


@router.get("/approvals")
def approval_analytics(db: Session = Depends(get_db)):
    return run_analytics_query(
        db,
        "03_approval_turnaround.sql",
    )


@router.get("/reimbursements")
def reimbursement_analytics(db: Session = Depends(get_db)):
    return run_analytics_query(
        db,
        "04_reimbursement_analytics.sql",
    )
