from app.core.security import verify_access_token
from app.db.models import UserAccount


def test_admin_auth_fixture(admin_auth_headers, db_session):
    authorization = admin_auth_headers["Authorization"]

    assert authorization.startswith("Bearer ")

    token = authorization.split(" ", 1)[1]
    user_id = verify_access_token(token)

    assert user_id is not None

    user = db_session.get(UserAccount, user_id)

    assert user is not None
    assert user.role == "ADMIN"
    assert user.is_active is True