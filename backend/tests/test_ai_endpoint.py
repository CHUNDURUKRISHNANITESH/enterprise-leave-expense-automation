
"""End-to-end AI Policy Assistant API tests using mocked OpenAI."""

import re

from datetime import date
from unittest.mock import patch
from uuid import uuid4

from app.db.models.models import LeavePolicy


AI_URL = "/api/v1/ai/ask"


def create_leave_policy(db_session):
    policy = LeavePolicy(
        id=f"LP-{uuid4().hex[:27]}",
        policy_code=f"ANNUAL-{uuid4().hex[:8]}",
        name="Annual Leave Policy",
        leave_type="ANNUAL",
        country="IN",
        annual_entitlement=20,
        accrual_frequency="MONTHLY",
        carryover_limit=5,
        max_consecutive_days=10,
        requires_documentation_after_days=3,
        is_paid=True,
        effective_from=date(2025, 1, 1),
        effective_to=None,
        description="Employees receive 20 days of annual leave.",
        rules={},
        version=1,
    )

    db_session.add(policy)
    db_session.commit()
    return policy


def test_ai_requires_authentication(client):
    response = client.post(
        AI_URL,
        json={"question": "What is my annual leave entitlement?"},
    )

    assert response.status_code == 401


def test_ai_retrieves_policy_sources(
    client, db_session, admin_auth_headers
):
    create_leave_policy(db_session)

    with patch(
        "app.api.v1.endpoints.ai.generate_grounded_answer",
        return_value=None,
    ):
        response = client.post(
            AI_URL,
            json={"question": "What is my annual leave entitlement?"},
            headers=admin_auth_headers,
        )

    assert response.status_code == 200

    data = response.json()

    assert data["mode"] == "retrieval-only"
    assert len(data["sources"]) > 0
    assert "Annual Leave Policy" in data["answer"]


def test_ai_returns_mocked_llm_answer(
    client, db_session, admin_auth_headers
):
    create_leave_policy(db_session)

    mock_answer = (
        "Employees receive 20 days of annual leave "
        "according to the Annual Leave Policy."
    )

    with patch(
        "app.api.v1.endpoints.ai.generate_grounded_answer",
        return_value=mock_answer,
    ) as mock_generate:
        response = client.post(
            AI_URL,
            json={"question": "How many annual leave days do I get?"},
            headers=admin_auth_headers,
        )

    assert response.status_code == 200

    data = response.json()

    assert data["mode"] == "llm-grounded"
    assert data["answer"] == mock_answer
    assert len(data["sources"]) > 0

    mock_generate.assert_called_once()

    question, context = mock_generate.call_args.args

    assert question == "How many annual leave days do I get?"

    assert re.search(r"Annual entitlement:\s*20(?:\.0+)?\s+days", context)


def test_ai_unknown_question_uses_fallback(
    client, db_session, admin_auth_headers
):
    create_leave_policy(db_session)

    with patch(
        "app.api.v1.endpoints.ai.generate_grounded_answer"
    ) as mock_generate:
        response = client.post(
            AI_URL,
            json={"question": "What is the spaceship fuel policy?"},
            headers=admin_auth_headers,
        )

    assert response.status_code == 200

    data = response.json()

    assert data["mode"] == "retrieval-only"
    assert data["sources"] == []

    mock_generate.assert_not_called()


def test_ai_rejects_invalid_question(
    client, admin_auth_headers
):
    response = client.post(
        AI_URL,
        json={"question": "Hi"},
        headers=admin_auth_headers,
    )

    assert response.status_code == 422
