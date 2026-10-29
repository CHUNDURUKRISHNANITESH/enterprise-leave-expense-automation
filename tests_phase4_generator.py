from decimal import Decimal
import pytest
from generator.config import GeneratorConfig
from generator.cli import generate
from generator.validators import validate_dataset
from generator.load_postgres import load

def test_generated_dataset():
    config = GeneratorConfig(seed=20261022, employee_count=30, leave_request_count=50, expense_claim_count=60)
    a = generate(config)
    b = generate(config)
    assert a == b
    assert len(a['leave_requests']) == 50
    assert len(a['expense_claims']) == 60
    assert len(a['audit_events']) == 330
    assert validate_dataset(a)
    assert all(1 <= sum(x['claim_id']==c['id'] for x in a['expense_lines']) <= 10 for c in a['expense_claims'])
    assert sum(Decimal(c['committed_amount']) for c in a['cost_centers']) == sum(Decimal(e['total_amount']) for e in a['expense_claims'] if e['status']=='APPROVED')

def test_loader_refuses_production_database():
    data = generate(GeneratorConfig(employee_count=30, leave_request_count=5, expense_claim_count=5))
    with pytest.raises(ValueError, match='Safety check'):
        load(data, 'postgresql+psycopg://postgres:postgres@localhost:5432/leave_expense', confirm_db='leave_expense', write=True)
