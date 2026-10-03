"""
Shared file discovery for the loaders, with IngestionLimits enforced.
"""

from pathlib import Path
from typing import Callable, Iterator, List, Sequence, TypeVar

from autorca_core.logging import get_logger
from autorca_core.validation import (
    IngestionLimits,
    ValidationError,
    check_file_size,
    sanitize_error_message,
    validate_path,
)

logger = get_logger(__name__)

T = TypeVar("T")


def load_source(
    source_path: Path,
    patterns: Sequence[str],
    load_file: Callable[[Path], List[T]],
    limits: IngestionLimits,
) -> List[T]:
    """
    Load records from a single file, or from every matching file below a directory.

    A single file that exceeds the size limit raises FileSizeError. In a directory,
    files that are too large, unreadable, or resolve outside the directory (for
    example through a symlink) are skipped with a warning, and discovery stops after
    ``max_files_per_directory`` files or once ``max_total_events`` records are loaded.

    Args:
        source_path: File or directory to load from
        patterns: Glob patterns matched recursively below a directory (e.g. "*.log")
        load_file: Parser for one file
        limits: Ingestion limits to enforce

    Returns:
        At most ``limits.max_total_events`` records
    """
    if source_path.is_file():
        check_file_size(source_path, limits)
        records = list(load_file(source_path))
    else:
        records = []
        for file_path in _iter_source_files(source_path, patterns, limits):
            if len(records) >= limits.max_total_events:
                logger.warning(
                    f"Reached event limit ({limits.max_total_events}), skipping remaining files"
                )
                break
            try:
                records.extend(load_file(file_path))
            except (OSError, UnicodeDecodeError, ValidationError) as e:
                logger.warning(
                    f"Skipping file {file_path.name}: {sanitize_error_message(e, file_path)}"
                )

    if len(records) > limits.max_total_events:
        logger.warning(
            f"Reached event limit ({limits.max_total_events}), "
            f"ignoring {len(records) - limits.max_total_events} records"
        )
        records = records[: limits.max_total_events]
    return records


def _iter_source_files(
    source_path: Path, patterns: Sequence[str], limits: IngestionLimits
) -> Iterator[Path]:
    """Yield matching files below source_path that pass the path and size checks."""
    file_count = 0
    for pattern in patterns:
        for file_path in source_path.glob(f"**/{pattern}"):
            if not file_path.is_file():
                continue
            try:
                validate_path(source_path, file_path)
                check_file_size(file_path, limits)
            except ValidationError as e:
                logger.warning(
                    f"Skipping file {file_path.name}: {sanitize_error_message(e, file_path)}"
                )
                continue
            if file_count >= limits.max_files_per_directory:
                logger.warning(
                    f"Reached file limit ({limits.max_files_per_directory}), "
                    "skipping remaining files"
                )
                return
            file_count += 1
            yield file_path
