
"""Verify that EMPLOYEE users cannot initiate reimbursements."""

import json
import os
import urllib.error
import urllib.request
from getpass import getpass

BASE_URL = "http://127.0.0.1:8000"
EMAIL = "generated.employee.000002@example.com"

# Safety check: never run against the original Phase 3 database.
database_url = os.environ.get("DATABASE_URL", "")
if not database_url.endswith("/leave_expense_synthetic"):
    raise SystemExit(
        "STOP: DATABASE_URL must point to leave_expense_synthetic."
    )


def post_json(path, payload, token=None):
    headers = {"Content-Type": "application/json"}

    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        BASE_URL + path,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.loads(
            error.read().decode("utf-8")
        )


password = getpass("Enter requester password: ")

login_status, login = post_json(
    "/api/v1/auth/login",
    {"email": EMAIL, "password": password},
)

if login_status != 200:
    print("Login failed:", login_status)
    raise SystemExit(1)

print("Requester login: HTTP", login_status)

status, result = post_json(
    "/api/v1/reimbursements",
    {
        "claim_id": "EXP-2026-000001",
        "idempotency_key": "phase4-employee-permission-test-001",
    },
    token=login["access_token"],
)

print("Reimbursement creation: HTTP", status)
print("Response:", result)

if status == 403:
    print("PASS: EMPLOYEE cannot initiate reimbursement.")
else:
    raise SystemExit(
        "FAIL: Expected HTTP 403. Check reimbursement authorization."
    )
