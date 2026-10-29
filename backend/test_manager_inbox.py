
import json
import urllib.request
import urllib.error
from getpass import getpass

BASE_URL = "http://127.0.0.1:8000"
EMAIL = "generated.employee.000001@example.com"
CLAIM_ID = "EXP-2026-000001"


def api_request(path, token=None, payload=None):
    headers = {"Content-Type": "application/json"}

    if token:
        headers["Authorization"] = f"Bearer {token}"

    data = json.dumps(payload).encode() if payload is not None else None

    request = urllib.request.Request(
        BASE_URL + path,
        data=data,
        headers=headers,
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.load(response)

    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode())


password = getpass("Enter ADMIN/manager password: ")

status, login = api_request(
    "/api/v1/auth/login",
    payload={"email": EMAIL, "password": password},
)

if status != 200:
    print("Login failed:", status, login)
    raise SystemExit(1)

print("Manager login:", status)

status, inbox = api_request(
    "/api/v1/approvals/inbox",
    token=login["access_token"],
)

print("Inbox HTTP status:", status)

if status != 200:
    print("Response:", inbox)
    raise SystemExit(1)

print("Pending actionable steps:", len(inbox))

matching = [
    step for step in inbox
    if step.get("expense_claim_id") == CLAIM_ID
]

if matching:
    step = matching[0]
    print("Target claim found: YES")
    print("Claim ID:", step["expense_claim_id"])
    print("Approval step:", step["step_number"])
    print("Assigned approver:", step["approver_employee_id"])
    print("Status:", step["status"])
else:
    print("Target claim found: NO")
