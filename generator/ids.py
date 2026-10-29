def employee_id(n: int) -> str:
    return f"EMP-{n:06d}"

def leave_request_id(n: int, year: int = 2026) -> str:
    return f"LVE-{year}-{n:06d}"

def expense_claim_id(n: int, year: int = 2026) -> str:
    return f"EXP-{year}-{n:06d}"

def expense_line_id(claim_id: str, line_number: int) -> str:
    return f"EXPL-{claim_id}-{line_number:02d}"

def approval_step_id(request_id: str, step_number: int) -> str:
    return f"APR-{request_id}-{step_number:02d}"

def reimbursement_id(n: int, year: int = 2026) -> str:
    return f"RMB-{year}-{n:06d}"
