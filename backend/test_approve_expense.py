
import json
import urllib.request
import urllib.error
from getpass import getpass

BASE_URL = "http://127.0.0.1:8000"
EMAIL = "generated.employee.000001@example.com"
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
        body = error.read().decode("utf-8")
        try:
            return error.code, json.loads(body)
        except json.JSONDecodeError:
            return error.code, {"detail": body}

    except urllib.error.URLError as error:
        print("Connection error:", error.reason)
        raise SystemExit(1)


password = getpass("Enter ADMIN/manager password: ")

status, login = post_json(
    "/api/v1/auth/login",
    {"email": EMAIL, "password": password},
)

if status != 200:
    print("Manager login failed:", status, login)
    raise SystemExit(1)

print("Manager login HTTP status:", status)

confirm = input(
    f"Approve expense {CLAIM_ID} for INR 500? Type APPROVE: "
)

if confirm != "APPROVE":
    print("Approval cancelled.")
    raise SystemExit(0)

status, result = post_json(
    f"/api/v1/approvals/expenses/{CLAIM_ID}/approve",
    {"reason": "Verified business meal expense and receipt"},
    token=login["access_token"],
)

print("\nApproval HTTP status:", status)
print("Approval response:", json.dumps(result, indent=2))

if status == 200:
    print("\nApproval API call successful.")
else:
    print("\nApproval API call did not succeed.")
