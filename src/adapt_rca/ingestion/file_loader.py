from pathlib import Path
from typing import Iterable, Dict
import json

def load_jsonl(path: str | Path) -> Iterable[Dict]:
    path = Path(path)
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                # Could add logging here
                continue
