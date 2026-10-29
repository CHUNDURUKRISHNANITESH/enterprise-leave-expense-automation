from datetime import date
from app.ai.retrieval import PolicyDocument, chunk_document, retrieve


def document(source, text, start=date(2025, 1, 1), end=None):
    return PolicyDocument(source, source, text, start, end)


def test_retrieves_matching_policy():
    docs = [document('annual', 'Annual leave entitlement twenty days'), document('travel', 'Travel hotel expense receipt limit')]
    results = retrieve('annual leave entitlement', docs, as_of=date(2026, 10, 29))
    assert results[0].source_id == 'annual'


def test_excludes_expired_or_future_policies():
    docs = [document('expired', 'annual leave', end=date(2025, 12, 31)), document('future', 'annual leave', start=date(2027, 1, 1))]
    assert retrieve('annual leave', docs, as_of=date(2026, 10, 29)) == []


def test_unknown_question_has_no_sources():
    assert retrieve('spaceship fuel', [document('annual', 'Annual leave')]) == []


def test_chunks_overlap():
    chunks = chunk_document(document('p', 'one two three four five six seven'), max_words=4, overlap=2)
    assert chunks[0].text == 'one two three four'
    assert chunks[1].text == 'three four five six'


def test_invalid_chunk_parameters():
    try:
        chunk_document(document('p', 'some text'), max_words=2, overlap=2)
    except ValueError:
        pass
    else:
        assert False, 'Expected ValueError'


def test_expense_question_excludes_leave_policies():
    docs = [
        document(
            "Leave policy LP-001",
            "Annual leave entitlement and employee leave rules",
        ),
        document(
            "Expense policy EP-001",
            "Travel expense reimbursement maximum amount 50000 INR",
        ),
        document(
            "Expense policy EP-002",
            "Lodging expense reimbursement maximum amount 30000 INR",
        ),
    ]

    results = retrieve(
        "What is the maximum travel expense reimbursement?",
        docs,
        as_of=date(2026, 10, 29),
    )

    assert results
    assert results[0].source_id == "Expense policy EP-001"
    assert all(
        result.source_id.startswith("Expense policy")
        for result in results
    )
