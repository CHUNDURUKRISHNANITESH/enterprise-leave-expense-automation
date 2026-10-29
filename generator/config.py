from dataclasses import dataclass

@dataclass(frozen=True)
class GeneratorConfig:
    seed: int = 20261022
    employee_count: int = 400
    leave_policy_count: int = 6
    leave_request_count: int = 800
    expense_claim_count: int = 1000
    min_lines_per_claim: int = 1
    max_lines_per_claim: int = 10
