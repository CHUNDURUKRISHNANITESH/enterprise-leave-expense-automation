"""Generate deterministic master data JSON without modifying PostgreSQL."""
import argparse
import json
from pathlib import Path

try:
    from .config import GeneratorConfig
    from .master_data import generate_master_data
except ImportError:
    from config import GeneratorConfig
    from master_data import generate_master_data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20261022)
    parser.add_argument("--employees", type=int, default=400)
    parser.add_argument("--leave-policies", type=int, default=6)
    parser.add_argument("--output", default="generated_data/master_data.json")
    args = parser.parse_args()
    config = GeneratorConfig(seed=args.seed, employee_count=args.employees,
                             leave_policy_count=args.leave_policies)
    data = generate_master_data(config)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Saved: {path}")
    for name, records in data.items():
        print(f"{name}: {len(records)}")


if __name__ == "__main__":
    main()
