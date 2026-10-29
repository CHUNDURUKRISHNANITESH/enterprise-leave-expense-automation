
import getpass
import json
import urllib.error
import urllib.request

BASE_URL = "http://127.0.0.1:8000/api/v1"

email = "generated.employee.000001@example.com"
password = getpass.getpass("Enter your test ADMIN password: ")

login_payload = json.dumps({
    "email": email,
    "password": password,
}).encode("utf-8")

login_request = urllib.request.Request(
    f"{BASE_URL}/auth/login",
    data=login_payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)

try:
    with urllib.request.urlopen(login_request) as response:
        login_data = json.load(response)

    print("Login: SUCCESS")

    dashboard_request = urllib.request.Request(
        f"{BASE_URL}/dashboard/summary",
        headers={
            "Authorization": f"Bearer {login_data['access_token']}"
        },
    )

    with urllib.request.urlopen(dashboard_request) as response:
        print("Dashboard HTTP status:", response.status)
        print(json.dumps(json.load(response), indent=2))

except urllib.error.HTTPError as error:
    print("HTTP error:", error.code)
    print(error.read().decode("utf-8"))

except urllib.error.URLError as error:
    print("Connection error:", error.reason)
