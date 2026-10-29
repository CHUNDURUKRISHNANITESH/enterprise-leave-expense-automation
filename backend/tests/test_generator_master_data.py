from generator.config import GeneratorConfig
from generator.master_data import generate_master_data


def test_master_data_counts_and_references():
    data = generate_master_data(GeneratorConfig(seed=20261022, employee_count=30, leave_policy_count=6))
    assert {k: len(v) for k, v in data.items()} == {
        "employees": 30, "cost_centers": 18, "leave_policies": 6,
        "expense_policies": 9, "approval_rules": 3,
    }
    assert data == generate_master_data(GeneratorConfig(seed=20261022, employee_count=30, leave_policy_count=6))
