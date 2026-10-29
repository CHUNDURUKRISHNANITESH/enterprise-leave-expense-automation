"""Dependency-free BM25-style policy retrieval, with document chunking and source IDs."""
from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

STOP = frozenset(['a', 'an', 'and', 'are', 'can', 'do', 'does', 'for', 'how', 'i', 'in', 'is', 'me', 'my', 'of', 'on', 'or', 'the', 'to', 'what', 'when', 'where', 'which', 'with', 'policy', 'policies', 'please', 'tell', 'about'])


def tokenize(text: str) -> list[str]:
    return [word for word in re.findall(r'[a-z0-9]+', text.lower()) if word not in STOP]


@dataclass(frozen=True)
class PolicyDocument:
    source_id: str
    title: str
    text: str
    effective_from: date
    effective_to: date | None


@dataclass(frozen=True)
class RetrievedChunk:
    source_id: str
    title: str
    text: str
    score: float


def chunk_document(document: PolicyDocument, max_words: int = 115, overlap: int = 20) -> list[RetrievedChunk]:
    if max_words <= overlap or overlap < 0:
        raise ValueError('max_words must be greater than nonnegative overlap')
    words = document.text.split()
    if not words:
        return []
    chunks = []
    for start in range(0, len(words), max_words - overlap):
        piece = words[start:start + max_words]
        if not piece:
            break
        chunks.append(RetrievedChunk(document.source_id, document.title, ' '.join(piece), 0.0))
        if start + max_words >= len(words):
            break
    return chunks



def retrieve(
    question: str,
    documents: Iterable[PolicyDocument],
    *,
    as_of: date | None = None,
    top_k: int = 4,
) -> list[RetrievedChunk]:
    """Rank effective policies using category-aware BM25 retrieval."""

    today = as_of or date.today()
    query = set(tokenize(question))

    if not query or top_k <= 0:
        return []

    documents = [
        document
        for document in documents
        if document.effective_from <= today
        and (
            document.effective_to is None
            or document.effective_to >= today
        )
    ]

    # Identify the question's policy domain.
    expense_keywords = {
        "expense", "expenses", "reimbursement", "reimburse",
        "travel", "hotel", "lodging", "meals", "receipt",
        "receipts", "claim", "claims",
    }

    leave_keywords = {
        "leave", "leaves", "vacation", "sick",
        "absence", "entitlement", "carryover", "accrual",
    }

    expense_matches = len(query & expense_keywords)
    leave_matches = len(query & leave_keywords)

    if expense_matches > leave_matches:
        matching_documents = [
            document
            for document in documents
            if document.source_id.lower().startswith("expense policy")
        ]

        if matching_documents:
            documents = matching_documents

    elif leave_matches > expense_matches:
        matching_documents = [
            document
            for document in documents
            if document.source_id.lower().startswith("leave policy")
        ]

        if matching_documents:
            documents = matching_documents

    candidates = [
        chunk
        for document in documents
        for chunk in chunk_document(document)
    ]

    if not candidates:
        return []

    counts = [
        Counter(tokenize(chunk.title + " " + chunk.text))
        for chunk in candidates
    ]

    avg_length = (
        sum(sum(count.values()) for count in counts)
        / len(counts)
    )

    df = Counter(
        word
        for count in counts
        for word in count
    )

    ranked = []

    for chunk, count in zip(candidates, counts):
        length = sum(count.values())
        score = 0.0

        for word in query:
            tf = count[word]

            if not tf:
                continue

            idf = math.log(
                1
                + (len(candidates) - df[word] + 0.5)
                / (df[word] + 0.5)
            )

            score += (
                idf * (tf * 2.2)
                / (
                    tf
                    + 1.2
                    * (
                        0.25
                        + 0.75
                        * length
                        / max(avg_length, 1)
                    )
                )
            )

        if score > 0:
            ranked.append(
                RetrievedChunk(
                    chunk.source_id,
                    chunk.title,
                    chunk.text,
                    score,
                )
            )

    ranked.sort(
        key=lambda chunk: (-chunk.score, chunk.source_id)
    )

    unique = []
    seen = set()

    for chunk in ranked:
        if chunk.source_id not in seen:
            unique.append(chunk)
            seen.add(chunk.source_id)

        if len(unique) >= top_k:
            break

    return unique





