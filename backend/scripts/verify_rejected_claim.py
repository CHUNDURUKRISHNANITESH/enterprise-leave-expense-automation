
import json
import os
import urllib.error
import urllib.request

BASE_URL = "http://127.0.0.1:8000/api/v1"
CLAIM_ID = "EXP-2026-000003"

password = os.environ.get("PHASE3_SEED_PASSWORD")
if not password:
    raise RuntimeError("PHASE3_SEED_PASSWORD is not set.")


def post(path, payload, token=None):
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
        with urllib.request.urlopen(request) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8")
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            pass
        return error.code, body


login_status, login = post(
    "/auth/login",
    {
        "email": "phase3.approver@example.com",
        "password": password,
    },
)

print("Second approver login:", login_status)

if login_status != 200:
    raise RuntimeError("Approver authentication failed.")

status, result = post(
    f"/approvals/expenses/{CLAIM_ID}/approve",
    {"reason": "Testing approval prevention after rejection."},
    login["access_token"],
)

print("Approval attempt HTTP status:", status)
print("API response:", json.dumps(result, indent=2))

assert status in (400, 409, 422), (
    f"Expected rejection of approval attempt, received HTTP {status}"
)

print("PASS: Rejected claim cannot be approved.")
