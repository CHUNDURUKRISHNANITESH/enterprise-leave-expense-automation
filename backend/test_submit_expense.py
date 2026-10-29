
import json
import urllib.request
import urllib.error
from getpass import getpass

BASE_URL = "http://127.0.0.1:8000"
EMAIL = "generated.employee.000002@example.com"
CLAIM_ID = "EXP-2026-000001"


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
    except urllib.error.URLError as error:
        print("Connection error:", error.reason)
        raise SystemExit(1)


password = getpass("Enter requester password: ")

status, login = post_json(
    "/api/v1/auth/login",
    {"email": EMAIL, "password": password},
)

if status != 200:
    print("Login failed:", status, login)
    raise SystemExit(1)

status, result = post_json(
    f"/api/v1/expenses/{CLAIM_ID}/submit",
    {},
    token=login["access_token"],
)

print("\nSubmission HTTP status:", status)

if status == 200:
    print("Claim ID:", result["id"])
    print("Employee:", result["employee_id"])
    print("Amount:", result["total_amount"])
    print("Status:", result["status"])
else:
    print("Response:", result)
