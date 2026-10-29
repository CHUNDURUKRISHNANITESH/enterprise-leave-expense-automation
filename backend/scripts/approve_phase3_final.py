
"""Complete second-level expense approval through FastAPI."""

import json
import os
import urllib.error
import urllib.request

BASE_URL = "http://127.0.0.1:8000/api/v1"
PASSWORD = os.environ["PHASE3_SEED_PASSWORD"]

with open("phase3_claim_id.txt", encoding="utf-8") as file:
    claim_id = file.read().strip()


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
        print(error.read().decode())
        raise


status, login = post(
    "/auth/login",
    {
        "email": "phase3.approver@example.com",
        "password": PASSWORD,
    },
)

print("Second approver login:", status)

status, result = post(
    f"/approvals/expenses/{claim_id}/approve",
    {
        "reason": "Travel expense reviewed and approved at final level."
    },
    login["access_token"],
)

print("Approval HTTP status:", status)
print("Claim ID:", result["claim_id"])
print("Final claim status:", result["status"])
print("Second approval status:", result["step_status"])
