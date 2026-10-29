"""JSON export for reproducible datasets."""
import json
from pathlib import Path

def export_json(data, path):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, sort_keys=True), encoding='utf-8')
    return target
