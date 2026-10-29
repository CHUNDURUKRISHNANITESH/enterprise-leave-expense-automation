# AI / RAG Design

PolicyPilot AI retrieves policy documents and effective versions, then answers with evidence and citations. For claim explanations, use a read-only backend tool to fetch the persisted claim, approval steps, and decision reasons.

The LLM must not independently approve claims, change balances, or create reimbursements. If policy evidence is missing or ambiguous, say so. Evaluate retrieval, citation support, answer correctness, and unsupported-answer rate.
