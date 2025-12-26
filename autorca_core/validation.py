"""
Input validation and security controls for AutoRCA-Core.

Provides path validation, size limits, and sanitization to prevent security issues.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class IngestionLimits:
    """
    Limits for data ingestion to prevent resource exhaustion.

    Attributes:
        max_file_size_mb: Maximum file size in megabytes
        max_total_events: Maximum number of events to ingest
        max_line_length: Maximum length of a single line
        max_files_per_directory: Maximum files to process from a directory
    """

    max_file_size_mb: float = 100.0
    max_total_events: int = 1_000_000
    max_line_length: int = 65536  # 64KB per line
    max_files_per_directory: int = 1000

    @classmethod
    def strict(cls) -> "IngestionLimits":
        """Create strict limits for untrusted data."""
        return cls(
            max_file_size_mb=10.0,
            max_total_events=100_000,
            max_line_length=8192,
            max_files_per_directory=100,
        )

    @classmethod
    def relaxed(cls) -> "IngestionLimits":
        """Create relaxed limits for trusted data."""
        return cls(
            max_file_size_mb=500.0,
            max_total_events=10_000_000,
            max_line_length=131072,  # 128KB
            max_files_per_directory=10000,
        )


class ValidationError(Exception):
    """Base exception for validation errors."""

    pass


class PathTraversalError(ValidationError):
    """Raised when path traversal is detected."""

    pass


class FileSizeError(ValidationError):
    """Raised when file size exceeds limits."""

    pass


class LineLengthError(ValidationError):
    """Raised when line length exceeds limits."""

    pass


def validate_path(source_path: Path, file_path: Path) -> bool:
    """
    Ensure file_path is within source_path to prevent path traversal attacks.

    Args:
        source_path: The expected root directory
        file_path: The file path to validate

    Returns:
        True if path is safe, False otherwise

    Raises:
        PathTraversalError: If path traversal is detected
    """
    try:
        # Resolve both paths to absolute paths
        source_resolved = source_path.resolve()
        file_resolved = file_path.resolve()

        # Check if file_path is within source_path
        file_resolved.relative_to(source_resolved)
        return True
    except ValueError:
        raise PathTraversalError(
            f"Path traversal detected: {file_path} is outside {source_path}"
        )


def check_file_size(file_path: Path, limits: IngestionLimits) -> None:
    """
    Check if file size is within limits.

    Args:
        file_path: Path to the file
        limits: Ingestion limits configuration

    Raises:
        FileSizeError: If file exceeds size limit
    """
    try:
        size_mb = file_path.stat().st_size / (1024 * 1024)
        if size_mb > limits.max_file_size_mb:
            raise FileSizeError(
                f"File size {size_mb:.1f}MB exceeds limit of {limits.max_file_size_mb}MB"
            )
    except OSError as e:
        raise ValidationError(f"Error checking file size: {e}")


def check_line_length(line: str, limits: IngestionLimits) -> None:
    """
    Check if line length is within limits.

    Args:
        line: The line to check
        limits: Ingestion limits configuration

    Raises:
        LineLengthError: If line exceeds length limit
    """
    if len(line) > limits.max_line_length:
        raise LineLengthError(
            f"Line length {len(line)} exceeds limit of {limits.max_line_length}"
        )


def sanitize_error_message(error: Exception, file_path: Optional[Path] = None) -> str:
    """
    Sanitize error messages to avoid leaking sensitive path information.

    Args:
        error: The exception to sanitize
        file_path: Optional file path to redact

    Returns:
        Sanitized error message
    """
    message = str(error)

    # Redact absolute paths
    if file_path:
        message = message.replace(str(file_path.resolve()), f"<file:{file_path.name}>")

    # Redact home directory paths
    home = os.path.expanduser("~")
    if home in message:
        message = message.replace(home, "~")

    return message


def check_total_events(current_count: int, limits: IngestionLimits) -> None:
    """
    Check if total event count is within limits.

    Args:
        current_count: Current number of events
        limits: Ingestion limits configuration

    Raises:
        ValidationError: If event count exceeds limit
    """
    if current_count >= limits.max_total_events:
        raise ValidationError(
            f"Event count {current_count} exceeds limit of {limits.max_total_events}"
        )

