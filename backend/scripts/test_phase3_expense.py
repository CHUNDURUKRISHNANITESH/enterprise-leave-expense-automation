
"""Create a real Phase 3 expense claim through FastAPI."""

import json
import os
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8000/api/v1"
PASSWORD = os.environ["PHASE3_SEED_PASSWORD"]


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
        "email": "phase3.requester@example.com",
        "password": PASSWORD,
    },
)

token = login["access_token"]
print("Requester login:", status)

claim = {
    "employee_id": "EMP-P3-REQUESTER",
    "cost_center_id": "CC-P3-001",
    "expense_date": "2026-10-28",
    "description": "Client meeting travel expenses",
    "business_purpose": "Travel for client project discussion",
    "merchant": "Local Transport",
    "currency": "INR",
    "lines": [
        {
            "category": "TRAVEL",
            "description": "Taxi fare for client meeting",
            "expense_date": "2026-10-28",
            "quantity": 1,
            "unit_amount": 2500,
            "receipt_uri": "https://example.com/test-receipt.pdf",
            "receipt_hash": "phase3-test-receipt-002",
        }
    ],
}

status, result = post("/expenses", claim, token)

print("Expense creation:", status)
print("Claim ID:", result["id"])
print("Total amount:", result["total_amount"])
print("Status:", result["status"])

with open("phase3_claim_id.txt", "w", encoding="utf-8") as file:
    file.write(result["id"])

print("Claim ID saved to phase3_claim_id.txt")
