"""
Config/deployment change ingestion: Load config and deployment change events.

Used to correlate incidents with recent changes that may have caused issues.
"""

import yaml
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import date, datetime

from autorca_core.model.events import ChangeType, ConfigChange, to_utc
from autorca_core.ingestion._jsonio import read_json_records
from autorca_core.ingestion._sources import load_source
from autorca_core.logging import get_logger
from autorca_core.validation import IngestionLimits

logger = get_logger(__name__)


def load_configs(
    source: str,
    time_from: Optional[datetime] = None,
    time_to: Optional[datetime] = None,
    service_filter: Optional[str] = None,
    limits: Optional[IngestionLimits] = None,
) -> List[ConfigChange]:
    """
    Load config/deployment change events from a file or directory.

    Args:
        source: Path to config change file or directory
        time_from: Start of time window (inclusive)
        time_to: End of time window (inclusive)
        service_filter: Only include changes for this service
        limits: Optional ingestion limits (defaults to IngestionLimits())

    Returns:
        List of ConfigChange objects
    """
    source_path = Path(source)

    if not source_path.exists():
        raise FileNotFoundError(f"Config source not found: {source}")

    # A directory loads all .jsonl, .json, .yaml and .yml files below it.
    # (pathlib globs do not support brace expansion, so one pattern each.)
    changes = load_source(
        source_path,
        ['*.jsonl', '*.json', '*.yaml', '*.yml'],
        _load_config_file,
        limits or IngestionLimits(),
    )

    # Apply filters
    if time_from:
        time_from = to_utc(time_from)
        changes = [c for c in changes if c.timestamp >= time_from]
    if time_to:
        time_to = to_utc(time_to)
        changes = [c for c in changes if c.timestamp <= time_to]
    if service_filter:
        changes = [c for c in changes if c.service == service_filter]

    return sorted(changes, key=lambda c: c.timestamp)


def _load_config_file(file_path: Path) -> List[ConfigChange]:
    """Load a single config change file."""
    if file_path.suffix in ('.yaml', '.yml'):
        return _parse_yaml_configs(file_path)
    elif file_path.suffix in ('.jsonl', '.json'):
        return _parse_json_configs(file_path)
    else:
        logger.warning(f"Unsupported config file format: {file_path}")
        return []


def _parse_json_configs(file_path: Path) -> List[ConfigChange]:
    """Parse JSON or JSON Lines config change file."""
    changes = []
    for item in read_json_records(file_path):
        change = _parse_config_item(item)
        if change:
            changes.append(change)
    return changes


def _parse_yaml_configs(file_path: Path) -> List[ConfigChange]:
    """Parse YAML config change file."""
    changes = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

            if isinstance(data, list):
                for item in data:
                    change = _parse_config_item(item)
                    if change:
                        changes.append(change)
            elif isinstance(data, dict):
                change = _parse_config_item(data)
                if change:
                    changes.append(change)
    except yaml.YAMLError as e:
        logger.warning(f"Failed to parse YAML file {file_path}: {e}")

    return changes


def _parse_config_item(item: Dict[str, Any]) -> Optional[ConfigChange]:
    """Parse a single config change item."""
    if not isinstance(item, dict):
        return None
    try:
        timestamp_str = item.get('timestamp') or item.get('time') or item.get('deployed_at')
        if not timestamp_str:
            return None

        # YAML may already have parsed an unquoted timestamp into a datetime/date
        if not isinstance(timestamp_str, (datetime, date)):
            timestamp_str = str(timestamp_str)
        timestamp = to_utc(timestamp_str)
        service = item.get('service') or item.get('service_name', 'unknown')

        # Determine change type
        change_type_val = str(item.get('change_type') or item.get('type') or 'config').lower()
        change_type: ChangeType
        if change_type_val in ('deploy', 'deployment', 'release'):
            change_type = 'deployment'
        elif change_type_val in ('scale', 'scaling', 'autoscale'):
            change_type = 'scaling'
        elif change_type_val in ('config', 'configuration'):
            change_type = 'config'
        else:
            change_type = 'other'

        description = item.get('description') or item.get('message') or ''
        version_before = item.get('version_before') or item.get('old_version')
        version_after = item.get('version_after') or item.get('new_version') or item.get('version')
        changed_by = item.get('changed_by') or item.get('deployed_by') or item.get('user')

        # Extract tags
        tags = item.get('tags', {})
        if isinstance(tags, dict):
            tags = {str(k): str(v) for k, v in tags.items()}
        else:
            tags = {}

        return ConfigChange(
            timestamp=timestamp,
            service=service,
            change_type=change_type,
            description=description,
            version_before=version_before,
            version_after=version_after,
            changed_by=changed_by,
            tags=tags,
            raw_data=item,
        )
    except (ValueError, KeyError, TypeError):
        return None
