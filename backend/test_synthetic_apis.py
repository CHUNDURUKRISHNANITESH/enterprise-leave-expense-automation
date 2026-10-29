
import json
import urllib.request
import urllib.error
from getpass import getpass

BASE_URL = "http://127.0.0.1:8000"
EMAIL = "generated.employee.000001@example.com"


def request_api(path, token=None, payload=None):
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
            body = json.load(response)
            return response.status, body

    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode())


password = getpass("Enter ADMIN password: ")

status, login = request_api(
    "/api/v1/auth/login",
    payload={"email": EMAIL, "password": password},
)

print("LOGIN:", status)

if status != 200:
    print("Login failed:", login)
    raise SystemExit(1)

token = login["access_token"]

endpoints = {
    "Employees": "/api/v1/employees",
    "Leave requests": "/api/v1/leaves",
    "Expense claims": "/api/v1/expenses",
    "Approval inbox": "/api/v1/approvals/inbox",
}

for name, path in endpoints.items():
    status, result = request_api(path, token=token)

    print(f"\n{name}")
    print("HTTP status:", status)

    if isinstance(result, list):
        print("Returned records:", len(result))
    elif isinstance(result, dict):
        print("Response keys:", list(result.keys()))
        for key in ("total", "count", "items"):
            if key in result:
                value = result[key]
                print(
                    key + ":",
                    len(value) if isinstance(value, list) else value,
                )
        if status >= 400:
            print("Error:", result)
    else:
        print("Response type:", type(result).__name__)
