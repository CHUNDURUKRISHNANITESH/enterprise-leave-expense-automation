
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
        print("HTTP ERROR:", error.code)
        print(error.read().decode("utf-8"))
        raise


login_status, login = post(
    "/auth/login",
    {
        "email": "phase3.manager@example.com",
        "password": password,
    },
)

print("Manager login:", login_status)

reject_status, result = post(
    f"/approvals/expenses/{CLAIM_ID}/reject",
    {
        "reason": "Expense rejected during Phase 3 budget-release integration testing."
    },
    login["access_token"],
)

print("Rejection HTTP status:", reject_status)
print("Claim ID:", CLAIM_ID)
print("API response:", json.dumps(result, indent=2))
