
"""Verify duplicate reimbursement creation is rejected."""

import json
import os
import urllib.error
import urllib.request
from getpass import getpass

BASE_URL = "http://127.0.0.1:8000"
ADMIN_EMAIL = "generated.employee.000001@example.com"
CLAIM_ID = "EXP-2026-000001"

database_url = os.environ.get("DATABASE_URL", "")

if not database_url.split("?")[0].endswith("/leave_expense_synthetic"):
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


password = getpass("Enter ADMIN password: ")

login_status, login = post_json(
    "/api/v1/auth/login",
    {
        "email": ADMIN_EMAIL,
        "password": password,
    },
)

print("ADMIN login: HTTP", login_status)

if login_status != 200:
    raise SystemExit("FAIL: ADMIN login failed.")

status, result = post_json(
    "/api/v1/reimbursements",
    {
        "claim_id": CLAIM_ID,
        "idempotency_key": "phase4-duplicate-reimbursement-key-002",
    },
    token=login["access_token"],
)

print("Duplicate reimbursement attempt: HTTP", status)
print("Response:", result)

if status == 409:
    print("PASS: Duplicate reimbursement prevented.")
else:
    raise SystemExit(
        "FAIL: Expected HTTP 409 for duplicate reimbursement."
    )
