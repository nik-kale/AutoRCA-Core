"""
Metrics ingestion: Load and parse metric time-series data.

Supports CSV, JSON, and Prometheus-style formats.
"""

import csv
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from autorca_core.model.events import MetricPoint, to_utc
from autorca_core.ingestion._jsonio import read_json_records
from autorca_core.ingestion._sources import load_source
from autorca_core.logging import get_logger
from autorca_core.validation import IngestionLimits

logger = get_logger(__name__)


def load_metrics(
    source: str,
    time_from: Optional[datetime] = None,
    time_to: Optional[datetime] = None,
    service_filter: Optional[str] = None,
    metric_filter: Optional[str] = None,
    limits: Optional[IngestionLimits] = None,
) -> List[MetricPoint]:
    """
    Load metrics from a file or directory.

    Args:
        source: Path to metrics file or directory
        time_from: Start of time window (inclusive)
        time_to: End of time window (inclusive)
        service_filter: Only include metrics from this service
        metric_filter: Only include metrics with this name
        limits: Optional ingestion limits (defaults to IngestionLimits())

    Returns:
        List of MetricPoint objects
    """
    source_path = Path(source)

    if not source_path.exists():
        raise FileNotFoundError(f"Metrics source not found: {source}")

    # A directory loads all .csv, .jsonl and .json files below it
    metrics = load_source(
        source_path, ["*.csv", "*.jsonl", "*.json"], _load_metrics_file, limits or IngestionLimits()
    )

    # Apply filters
    if time_from:
        time_from = to_utc(time_from)
        metrics = [m for m in metrics if m.timestamp >= time_from]
    if time_to:
        time_to = to_utc(time_to)
        metrics = [m for m in metrics if m.timestamp <= time_to]
    if service_filter:
        metrics = [m for m in metrics if m.service == service_filter]
    if metric_filter:
        metrics = [m for m in metrics if m.metric_name == metric_filter]

    return sorted(metrics, key=lambda m: m.timestamp)


def _load_metrics_file(file_path: Path) -> List[MetricPoint]:
    """Load a single metrics file."""
    if file_path.suffix == ".csv":
        return _parse_csv_metrics(file_path)
    elif file_path.suffix in (".jsonl", ".json"):
        return _parse_json_metrics(file_path)
    else:
        logger.warning(f"Unsupported metrics file format: {file_path}")
        return []


def _parse_csv_metrics(file_path: Path) -> List[MetricPoint]:
    """
    Parse CSV metrics file.

    Expected columns: timestamp, service, metric_name, value, [unit], [tags...]
    """
    metrics = []

    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                timestamp_str = row.get("timestamp") or row.get("time")
                if not timestamp_str:
                    continue

                timestamp = to_utc(timestamp_str)
                service = row.get("service", "unknown")
                metric_name = row.get("metric_name") or row.get("metric", "unknown")
                value = float(row.get("value", 0.0))
                unit = row.get("unit")

                # Remaining columns are tags
                tags = {
                    k: v
                    for k, v in row.items()
                    if k
                    not in (
                        "timestamp",
                        "time",
                        "service",
                        "metric_name",
                        "metric",
                        "value",
                        "unit",
                    )
                }

                metrics.append(
                    MetricPoint(
                        timestamp=timestamp,
                        service=service,
                        metric_name=metric_name,
                        value=value,
                        unit=unit,
                        tags=tags,
                        raw_data=row,
                    )
                )
            except (ValueError, KeyError, TypeError) as e:
                logger.warning(f"Failed to parse CSV row in {file_path.name}: {e}")

    return metrics


def _parse_json_metrics(file_path: Path) -> List[MetricPoint]:
    """
    Parse JSON or JSON Lines metrics file.

    Each line/object should contain: timestamp, service, metric_name, value
    """
    metrics = []
    for item in read_json_records(file_path):
        metric = _parse_json_metric_item(item)
        if metric:
            metrics.append(metric)
    return metrics


def _parse_json_metric_item(item: Dict[str, Any]) -> Optional[MetricPoint]:
    """Parse a single JSON metric object."""
    if not isinstance(item, dict):
        return None
    try:
        timestamp_str = item.get("timestamp") or item.get("time")
        if not timestamp_str:
            return None

        timestamp = to_utc(timestamp_str)
        service = item.get("service") or item.get("service_name", "unknown")
        metric_name = item.get("metric_name") or item.get("metric") or item.get("name", "unknown")
        value = float(item.get("value", 0.0))
        unit = item.get("unit")

        # Extract tags
        tags = item.get("tags", {})
        if isinstance(tags, dict):
            tags = {str(k): str(v) for k, v in tags.items()}
        else:
            tags = {}

        return MetricPoint(
            timestamp=timestamp,
            service=service,
            metric_name=metric_name,
            value=value,
            unit=unit,
            tags=tags,
            raw_data=item,
        )
    except (ValueError, KeyError, TypeError):
        return None
