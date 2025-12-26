"""
Configuration module for AutoRCA-Core.

Provides configurable thresholds and settings for anomaly detection and RCA analysis.
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ThresholdConfig:
    """
    Configurable thresholds for anomaly detection.

    These thresholds control when incidents are detected from observability data.
    Different environments have different baselines, so these can be tuned accordingly.

    Attributes:
        # Error detection
        error_spike_count: Minimum number of errors to consider a spike
        error_spike_window_seconds: Time window for error spike detection

        # Latency detection
        latency_spike_ms: Latency threshold in milliseconds
        latency_spike_count: Minimum number of high-latency samples

        # Resource detection
        resource_exhaustion_percent: Resource usage percentage threshold
        resource_exhaustion_count: Minimum number of high-usage samples

        # Correlation windows
        change_correlation_seconds: Time window for correlating changes with incidents
    """

    # Error detection
    error_spike_count: int = 3
    error_spike_window_seconds: int = 300  # 5 minutes

    # Latency detection
    latency_spike_ms: float = 1000.0
    latency_spike_count: int = 2

    # Resource detection
    resource_exhaustion_percent: float = 90.0
    resource_exhaustion_count: int = 2

    # Correlation windows
    change_correlation_seconds: int = 600  # 10 minutes

    @classmethod
    def from_env(cls) -> "ThresholdConfig":
        """
        Load thresholds from environment variables.

        Environment variables:
            AUTORCA_ERROR_SPIKE_COUNT: Error spike count threshold
            AUTORCA_ERROR_SPIKE_WINDOW: Error spike window in seconds
            AUTORCA_LATENCY_SPIKE_MS: Latency spike threshold in ms
            AUTORCA_LATENCY_SPIKE_COUNT: Latency spike count threshold
            AUTORCA_RESOURCE_EXHAUSTION_PERCENT: Resource exhaustion percentage
            AUTORCA_RESOURCE_EXHAUSTION_COUNT: Resource exhaustion count threshold
            AUTORCA_CHANGE_CORRELATION_SECONDS: Change correlation window in seconds

        Returns:
            ThresholdConfig instance with values from environment
        """
        return cls(
            error_spike_count=int(os.getenv("AUTORCA_ERROR_SPIKE_COUNT", 3)),
            error_spike_window_seconds=int(os.getenv("AUTORCA_ERROR_SPIKE_WINDOW", 300)),
            latency_spike_ms=float(os.getenv("AUTORCA_LATENCY_SPIKE_MS", 1000.0)),
            latency_spike_count=int(os.getenv("AUTORCA_LATENCY_SPIKE_COUNT", 2)),
            resource_exhaustion_percent=float(os.getenv("AUTORCA_RESOURCE_EXHAUSTION_PERCENT", 90.0)),
            resource_exhaustion_count=int(os.getenv("AUTORCA_RESOURCE_EXHAUSTION_COUNT", 2)),
            change_correlation_seconds=int(os.getenv("AUTORCA_CHANGE_CORRELATION_SECONDS", 600)),
        )

    @classmethod
    def strict(cls) -> "ThresholdConfig":
        """
        Create a strict configuration (more sensitive to anomalies).

        Returns:
            ThresholdConfig with strict thresholds
        """
        return cls(
            error_spike_count=2,
            error_spike_window_seconds=180,  # 3 minutes
            latency_spike_ms=500.0,
            latency_spike_count=1,
            resource_exhaustion_percent=80.0,
            resource_exhaustion_count=1,
            change_correlation_seconds=900,  # 15 minutes
        )

    @classmethod
    def relaxed(cls) -> "ThresholdConfig":
        """
        Create a relaxed configuration (less sensitive to anomalies).

        Returns:
            ThresholdConfig with relaxed thresholds
        """
        return cls(
            error_spike_count=5,
            error_spike_window_seconds=600,  # 10 minutes
            latency_spike_ms=2000.0,
            latency_spike_count=3,
            resource_exhaustion_percent=95.0,
            resource_exhaustion_count=3,
            change_correlation_seconds=300,  # 5 minutes
        )

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "error_spike_count": self.error_spike_count,
            "error_spike_window_seconds": self.error_spike_window_seconds,
            "latency_spike_ms": self.latency_spike_ms,
            "latency_spike_count": self.latency_spike_count,
            "resource_exhaustion_percent": self.resource_exhaustion_percent,
            "resource_exhaustion_count": self.resource_exhaustion_count,
            "change_correlation_seconds": self.change_correlation_seconds,
        }

