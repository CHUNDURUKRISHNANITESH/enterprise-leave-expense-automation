
from pathlib import Path
import re

path = Path("tests/test_leaves.py")
source = path.read_text(encoding="utf-8")

# Preserve the authentication helper.
helper_start = source.index("def submit_leave_request(")
test_start = source.index("\ndef test_", helper_start)

prefix = source[:test_start]
tests = source[test_start:]

# Replace direct submission calls inside tests only.
pattern = re.compile(
    r'client\.post\(\s*f"\{BASE_URL\}/\{leave_request_id\}/submit"\s*\)'
)

updated_tests, count = pattern.subn(
    "submit_leave_request(client, db_session, leave_request_id)",
    tests,
)

print(f"Found {count} unauthenticated submission calls.")

if count != 14:
    raise SystemExit(
        f"Expected 14 replacements, found {count}. No changes saved."
    )

path.write_text(prefix + updated_tests, encoding="utf-8")

print("Successfully updated 14 submission calls.")
