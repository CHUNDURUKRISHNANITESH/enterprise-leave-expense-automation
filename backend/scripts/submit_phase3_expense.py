
"""Submit the Phase 3 expense claim through the real FastAPI API."""

import json
import os
import urllib.request
import urllib.error

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
        "email": "phase3.requester@example.com",
        "password": PASSWORD,
    },
)

print("Requester login:", status)

status, result = post(
    f"/expenses/{claim_id}/submit",
    {},
    login["access_token"],
)

print("Submission HTTP status:", status)
print("Claim ID:", result["id"])
print("Total amount:", result["total_amount"])
print("Claim status:", result["status"])
