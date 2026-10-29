"""Deterministic master-data generation. No database writes."""
from __future__ import annotations

import random
from datetime import date
from decimal import Decimal
from typing import Any

from faker import Faker

try:
    from .config import GeneratorConfig
    from .ids import employee_id
except ImportError:
    from config import GeneratorConfig
    from ids import employee_id


COUNTRIES = {"IN": "INR", "US": "USD", "GB": "GBP"}
DEPARTMENTS = ("Engineering", "Finance", "Operations", "HR", "Sales", "Support")
LEAVE_TYPES = ("ANNUAL", "SICK")
EXPENSE_CATEGORIES = ("TRAVEL", "MEALS", "LODGING")


def generate_master_data(config: GeneratorConfig) -> dict[str, list[dict[str, Any]]]:
    if config.employee_count < 2:
        raise ValueError("At least two employees are required for a reporting hierarchy")
    if config.leave_policy_count < 1:
        raise ValueError("At least one leave policy is required")

    rng = random.Random(config.seed)
    fake = Faker("en_US")
    fake.seed_instance(config.seed)
    countries = tuple(COUNTRIES)
    employees: list[dict[str, Any]] = []
    centers: list[dict[str, Any]] = []

    # Parent-first ordering ensures every manager reference points to an earlier employee.
    for i in range(1, config.employee_count + 1):
        country = countries[((i - 1) // len(DEPARTMENTS)) % len(countries)]
        department = DEPARTMENTS[(i - 1) % len(DEPARTMENTS)]
        center_id = f"CC-GEN-{country}-{DEPARTMENTS.index(department)+1:02d}"
        manager_index = None if i == 1 else (1 if i <= 12 else max(1, (i - 2) // 6 + 1))
        first, last = fake.first_name(), fake.last_name()
        employees.append({
            "id": employee_id(i), "employee_number": f"GEN-{i:06d}",
            "first_name": first, "last_name": last,
            "email": f"generated.employee.{i:06d}@example.com",
            "job_title": "Team Lead" if i <= 12 else "Analyst",
            "department": department, "country": country,
            "currency": COUNTRIES[country],
            "manager_id": employee_id(manager_index) if manager_index else None,
            "cost_center_id": center_id,
            "employment_start_date": date(2022 + rng.randrange(4), rng.randint(1, 12), rng.randint(1, 28)).isoformat(),
            "employment_end_date": None, "employment_status": "ACTIVE",
            "is_approver": i <= 12, "attributes": {"synthetic": True},
        })

    # Every referenced manager must have approval authority for backend routing.
    manager_ids = {e["manager_id"] for e in employees if e["manager_id"]}
    for employee in employees:
        employee["is_approver"] = employee["id"] in manager_ids

    # One center per country/department, with a valid employee owner.
    for country in countries:
        for idx, department in enumerate(DEPARTMENTS, start=1):
            owner = next(e for e in employees if e["country"] == country and e["department"] == department)
            centers.append({
                "id": f"CC-GEN-{country}-{idx:02d}", "code": f"GEN-{department[:3].upper()}-{idx:02d}",
                "name": f"{country} {department}", "country": country,
                "owner_employee_id": owner["id"], "budget_amount": "1000000.00",
                "committed_amount": "0.00", "currency": COUNTRIES[country],
                "is_active": True, "attributes": {"synthetic": True},
            })

    leave_policies = []
    for i in range(config.leave_policy_count):
        country = countries[(i // len(LEAVE_TYPES)) % len(countries)]
        leave_type = LEAVE_TYPES[i % len(LEAVE_TYPES)]
        leave_policies.append({
            "id": f"LP-GEN-{i+1:03d}", "policy_code": f"GEN-{country}-{leave_type}",
            "name": f"{country} {leave_type.title()} Leave", "description": "Synthetic policy",
            "leave_type": leave_type, "country": country,
            "annual_entitlement": "20.00" if leave_type == "ANNUAL" else "10.00",
            "accrual_frequency": "ANNUAL", "carryover_limit": "5.00" if leave_type == "ANNUAL" else "0.00",
            "requires_documentation_after_days": 2 if leave_type == "SICK" else None,
            "max_consecutive_days": 15 if leave_type == "ANNUAL" else 10,
            "is_paid": True, "effective_from": "2026-01-01", "effective_to": None,
            "version": 1, "rules": {"business_days_only": True},
        })

    expense_policies = []
    for country in countries:
        for category in EXPENSE_CATEGORIES:
            expense_policies.append({
                "id": f"EP-GEN-{country}-{category}", "policy_code": f"GEN-{country}-{category}",
                "name": f"{country} {category.title()} Expense", "country": country,
                "category": category, "currency": COUNTRIES[country],
                "per_item_limit": "10000.00", "max_amount": "50000.00",
                "min_receipt_amount": "1.00", "receipt_required": True,
                "requires_business_purpose": True, "effective_from": "2026-01-01",
                "effective_to": None, "version": 1, "rules": {"synthetic": True},
            })

    approval_rules = []
    for country in countries:
        approval_rules.append({
            "id": f"AR-GEN-{country}-MANAGER", "name": f"{country} Manager Approval",
            "country": country, "category": None, "min_amount": "0.00",
            "max_amount": None, "currency": COUNTRIES[country],
            "approver_type": "MANAGER", "approver_role": None,
            "approver_employee_id": None, "approval_level": 1,
            "effective_from": "2026-01-01", "effective_to": None,
            "priority": 100, "is_active": True, "conditions": {},
        })

    result = {"employees": employees, "cost_centers": centers,
              "leave_policies": leave_policies, "expense_policies": expense_policies,
              "approval_rules": approval_rules}
    validate_master_data(result)
    return result


def validate_master_data(data: dict[str, list[dict[str, Any]]]) -> None:
    employees = data["employees"]
    ids = {e["id"] for e in employees}
    centers = {c["id"] for c in data["cost_centers"]}
    if len(ids) != len(employees):
        raise ValueError("Duplicate employee IDs")
    if len({e["email"] for e in employees}) != len(employees):
        raise ValueError("Duplicate employee emails")
    for e in employees:
        if e["manager_id"] is not None and e["manager_id"] not in ids:
            raise ValueError(f"Invalid manager for {e['id']}")
        if e["manager_id"] == e["id"]:
            raise ValueError(f"Self-manager for {e['id']}")
        if e["cost_center_id"] not in centers:
            raise ValueError(f"Invalid cost center for {e['id']}")
    for center in data["cost_centers"]:
        if center["owner_employee_id"] not in ids:
            raise ValueError(f"Invalid cost center owner for {center['id']}")
    for table, rows in data.items():
        if len({r["id"] for r in rows}) != len(rows):
            raise ValueError(f"Duplicate IDs in {table}")
