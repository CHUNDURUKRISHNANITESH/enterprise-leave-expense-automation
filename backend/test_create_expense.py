
import json
import urllib.request
import urllib.error
from getpass import getpass

BASE_URL = "http://127.0.0.1:8000"
EMAIL = "generated.employee.000002@example.com"


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
        return error.code, json.loads(error.read().decode("utf-8"))


password = getpass("Enter requester password: ")

status, login = post_json(
    "/api/v1/auth/login",
    {"email": EMAIL, "password": password},
)

if status != 200:
    print("Login failed:", status, login)
    raise SystemExit(1)

payload = {
    "employee_id": "EMP-000002",
    "cost_center_id": "CC-GEN-IN-01",
    "expense_date": "2026-10-28",
    "description": "Phase 4 approval workflow integration test",
    "business_purpose": "Meal expense during project work",
    "merchant": "Test Restaurant",
    "currency": "INR",
    "lines": [
        {
            "category": "MEALS",
            "description": "Business lunch",
            "expense_date": "2026-10-28",
            "quantity": "1",
            "unit_amount": "500.00",
            "receipt_uri": "https://example.com/receipts/phase4-meals-test.pdf",
            "receipt_hash": None,
        }
    ],
}

status, result = post_json(
    "/api/v1/expenses",
    payload,
    token=login["access_token"],
)

print("\nExpense creation HTTP status:", status)

if status == 201:
    print("Claim ID:", result["id"])
    print("Employee:", result["employee_id"])
    print("Amount:", result["total_amount"])
    print("Currency:", result["currency"])
    print("Status:", result["status"])
    print("Expense lines:", len(result["lines"]))
else:
    print("Response:", result)
