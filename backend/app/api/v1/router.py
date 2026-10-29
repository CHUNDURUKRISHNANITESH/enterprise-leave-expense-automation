
from app.api.v1.endpoints import (
    ai,
    analytics,
    approvals,
    auth,
    dashboard,
    employees,
    expenses,
    leaves,
    reimbursements,
)
from fastapi import APIRouter

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(employees.router)
api_router.include_router(leaves.router)
api_router.include_router(expenses.router)
api_router.include_router(approvals.router)
api_router.include_router(reimbursements.router)
api_router.include_router(dashboard.router)
api_router.include_router(ai.router)
api_router.include_router(analytics.router)
