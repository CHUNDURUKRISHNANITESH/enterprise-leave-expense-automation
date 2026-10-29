
import json
import urllib.request
import urllib.error
from getpass import getpass

BASE_URL = "http://127.0.0.1:8000/api/v1"
ADMIN_EMAIL = "generated.employee.000001@example.com"


def login_admin():
    password = getpass("Enter ADMIN password: ")

    payload = json.dumps({
        "email": ADMIN_EMAIL,
        "password": password,
    }).encode("utf-8")

    request = urllib.request.Request(
        f"{BASE_URL}/auth/login",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=10) as response:
        result = json.load(response)

        if response.status != 200:
            raise AssertionError("ADMIN login failed")

    token = result["access_token"]

    print("ADMIN login: PASSED")
    print("Token received: True")
    print()

    return token


def test_analytics_endpoint(token, endpoint, expected_count):
    request = urllib.request.Request(
        f"{BASE_URL}/analytics/{endpoint}",
        headers={
            "Authorization": f"Bearer {token}",
        },
        method="GET",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)
        status_code = response.status

    print(f"Endpoint: {endpoint}")
    print(f"HTTP status: {status_code}")
    print(f"Records returned: {len(data)}")
    print(f"Expected records: {expected_count}")

    assert status_code == 200, (
        f"Expected HTTP 200, received {status_code}"
    )

    assert isinstance(data, list), (
        f"{endpoint}: Expected JSON array"
    )

    assert len(data) == expected_count, (
        f"{endpoint}: Expected {expected_count} records, "
        f"received {len(data)}"
    )

    print(f"{endpoint}: PASSED")
    print("-" * 50)

    return data


def main():
    token = login_admin()

    endpoints = {
        "leave-utilization": 19,
        "expenses": 54,
        "approvals": 134,
        "reimbursements": 1,
    }

    passed = 0
    failed = 0

    for endpoint, expected_count in endpoints.items():
        try:
            test_analytics_endpoint(
                token,
                endpoint,
                expected_count,
            )
            passed += 1

        except urllib.error.HTTPError as error:
            print(f"{endpoint}: FAILED")
            print("HTTP error:", error.code)
            print(
                "Response:",
                error.read().decode("utf-8"),
            )
            failed += 1
            print("-" * 50)

        except (
            urllib.error.URLError,
            AssertionError,
            ValueError,
            TypeError,
        ) as error:
            print(f"{endpoint}: FAILED")
            print("Error:", error)
            failed += 1
            print("-" * 50)

    print()
    print("=" * 50)
    print("PHASE 7 - ANALYTICS API TEST SUMMARY")
    print("=" * 50)
    print("Total endpoints:", len(endpoints))
    print("Passed:", passed)
    print("Failed:", failed)

    if failed == 0:
        print("RESULT: ALL ANALYTICS API TESTS PASSED")
    else:
        print("RESULT: SOME ANALYTICS API TESTS FAILED")
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as error:
        print("Login HTTP error:", error.code)
        print(error.read().decode("utf-8"))
        raise SystemExit(1)
    except urllib.error.URLError as error:
        print("Connection error:", error.reason)
        raise SystemExit(1)
    except (KeyError, ValueError, AssertionError) as error:
        print("Authentication failed:", error)
        raise SystemExit(1)
