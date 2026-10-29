
"""Verify reimbursement creation is idempotent."""

import json
import os
import urllib.error
import urllib.request
from getpass import getpass

BASE_URL = "http://127.0.0.1:8000"
ADMIN_EMAIL = "generated.employee.000001@example.com"

CLAIM_ID = "EXP-2026-000001"
EXPECTED_REIMBURSEMENT_ID = "RMB-76e53c6eb3204e7585fc"
IDEMPOTENCY_KEY = "phase4-exp-2026-000001-reimbursement-v1"

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
    {"email": ADMIN_EMAIL, "password": password},
)

print("ADMIN login: HTTP", login_status)

if login_status != 200:
    raise SystemExit("FAIL: ADMIN login failed.")

status, result = post_json(
    "/api/v1/reimbursements",
    {
        "claim_id": CLAIM_ID,
        "idempotency_key": IDEMPOTENCY_KEY,
    },
    token=login["access_token"],
)

print("Repeated creation request: HTTP", status)

if status == 201:
    print("Returned reimbursement ID:", result["id"])
    print("Claim ID:", result["claim_id"])
    print("Current status:", result["status"])

    if (
        result["id"] == EXPECTED_REIMBURSEMENT_ID
        and result["claim_id"] == CLAIM_ID
        and result["status"] == "PAID"
    ):
        print("PASS: Existing reimbursement returned.")
    else:
        raise SystemExit("FAIL: Unexpected reimbursement returned.")
else:
    print("Response:", result)
    raise SystemExit("FAIL: Idempotency request failed.")
