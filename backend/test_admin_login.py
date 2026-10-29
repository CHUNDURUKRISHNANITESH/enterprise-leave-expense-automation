
import json
import urllib.request
import urllib.error
from getpass import getpass

email = "generated.employee.000001@example.com"
password = getpass("Enter ADMIN password: ")

payload = json.dumps({
    "email": email,
    "password": password,
}).encode("utf-8")

request = urllib.request.Request(
    "http://127.0.0.1:8000/api/v1/auth/login",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)

try:
    with urllib.request.urlopen(request, timeout=10) as response:
        result = json.load(response)

        print("HTTP status:", response.status)
        print("Token type:", result.get("token_type"))
        print("Token received:", bool(result.get("access_token")))
        print("Expires in:", result.get("expires_in"), "seconds")

except urllib.error.HTTPError as error:
    print("HTTP status:", error.code)
    print("Response:", error.read().decode("utf-8"))

except urllib.error.URLError as error:
    print("Connection error:", error.reason)
