"""
Shared JSON reading for the metrics, traces and config loaders.
"""

import json
from pathlib import Path
from typing import Any, List

from autorca_core.logging import get_logger

logger = get_logger(__name__)


def read_json_records(file_path: Path) -> List[Any]:
    """
    Read records from a JSON array, a single JSON object, or JSON Lines.

    A JSON Lines file with exactly one line is valid JSON on its own, so the
    whole-document parse is tried first and a top-level object is returned as a
    one-element list rather than being dropped.

    Args:
        file_path: Path to a .json or .jsonl file

    Returns:
        List of decoded records (not validated; callers skip non-dict items)
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        pass
    else:
        return data if isinstance(data, list) else [data]

    records: List[Any] = []
    for line_num, line in enumerate(content.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON line {line_num} in {file_path.name}: {e}")
    return records
