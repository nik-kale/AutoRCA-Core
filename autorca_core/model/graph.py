"""
Graph models: Service, Dependency, IncidentNode, and ServiceGraph.

These models represent the topology and causal relationships between services,
dependencies, and incident symptoms.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any
from datetime import datetime
from enum import Enum


class DependencyType(str, Enum):
    """Type of dependency between services."""
    HTTP = "http"
    DATABASE = "database"
    QUEUE = "queue"
    CACHE = "cache"
    DNS = "dns"
    UNKNOWN = "unknown"


class IncidentType(str, Enum):
    """Type of incident or symptom."""
    ERROR_SPIKE = "error_spike"
    LATENCY_SPIKE = "latency_spike"
    THROUGHPUT_DROP = "throughput_drop"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    CONFIG_CHANGE = "config_change"
    DEPLOYMENT = "deployment"
    UNKNOWN = "unknown"


@dataclass
class Service:
    """
    Represents a service node in the service graph.

    Attributes:
        name: Service identifier (e.g., "api-gateway", "user-service")
        service_type: Type of service (api, database, cache, etc.)
        metadata: Additional service metadata (version, region, etc.)
    """
    name: str
    service_type: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, Service):
            return self.name == other.name
        return False


@dataclass
class Dependency:
    """
    Represents a dependency edge between two services.

    Attributes:
        from_service: Source service name
        to_service: Target service name
        dependency_type: Type of dependency (HTTP, DB, queue, etc.)
        weight: Strength/frequency of dependency (higher = more calls)
        metadata: Additional edge metadata
    """
    from_service: str
    to_service: str
    dependency_type: DependencyType = DependencyType.UNKNOWN
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        return hash((self.from_service, self.to_service, self.dependency_type))

    def __eq__(self, other):
        if isinstance(other, Dependency):
            return (
                self.from_service == other.from_service
                and self.to_service == other.to_service
                and self.dependency_type == other.dependency_type
            )
        return False


@dataclass
class IncidentNode:
    """
    Represents an incident symptom or anomaly detected in a service.

    Attributes:
        service: Service where the incident occurred
        incident_type: Type of incident (error spike, latency, etc.)
        timestamp: When the incident was detected
        severity: Severity score (0.0 - 1.0, higher = more severe)
        description: Human-readable description
        evidence: Supporting evidence (log lines, metric values, etc.)
        metadata: Additional incident metadata
    """
    service: str
    incident_type: IncidentType
    timestamp: datetime
    severity: float = 0.5
    description: str = ""
    evidence: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure timestamp is a datetime object and severity is valid."""
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))
        self.severity = max(0.0, min(1.0, self.severity))


@dataclass
class ServiceGraph:
    """
    Service topology and dependency graph.

    This graph represents the runtime relationships between services and
    is used to propagate causal analysis during RCA.
    """
    services: Dict[str, Service] = field(default_factory=dict)
    dependencies: Set[Dependency] = field(default_factory=set)
    incidents: List[IncidentNode] = field(default_factory=list)

    def add_service(self, service: Service) -> None:
        """Add a service to the graph."""
        self.services[service.name] = service

    def add_dependency(self, dependency: Dependency) -> None:
        """
        Add a dependency edge to the graph.

        Automatically creates service nodes if they don't exist.
        """
        if dependency.from_service not in self.services:
            self.add_service(Service(name=dependency.from_service))
        if dependency.to_service not in self.services:
            self.add_service(Service(name=dependency.to_service))
        self.dependencies.add(dependency)

    def add_incident(self, incident: IncidentNode) -> None:
        """Add an incident node to the graph."""
        if incident.service not in self.services:
            self.add_service(Service(name=incident.service))
        self.incidents.append(incident)

    def get_dependencies_for_service(self, service_name: str) -> List[Dependency]:
        """Get all outbound dependencies for a service."""
        return [d for d in self.dependencies if d.from_service == service_name]

    def get_upstream_dependencies(self, service_name: str) -> List[Dependency]:
        """Get all services that depend on this service (upstream callers)."""
        return [d for d in self.dependencies if d.to_service == service_name]

    def get_incidents_for_service(self, service_name: str) -> List[IncidentNode]:
        """Get all incidents for a specific service."""
        return [i for i in self.incidents if i.service == service_name]

    def get_services_sorted_by_incident_severity(self) -> List[str]:
        """
        Return services sorted by total incident severity (highest first).

        Useful for prioritizing which services to investigate first.
        """
        severity_map: Dict[str, float] = {}
        for incident in self.incidents:
            severity_map[incident.service] = severity_map.get(incident.service, 0.0) + incident.severity
        return sorted(severity_map.keys(), key=lambda s: severity_map[s], reverse=True)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the graph to a dictionary."""
        return {
            "services": [{"name": s.name, "type": s.service_type, "metadata": s.metadata}
                        for s in self.services.values()],
            "dependencies": [
                {
                    "from": d.from_service,
                    "to": d.to_service,
                    "type": d.dependency_type.value,
                    "weight": d.weight,
                }
                for d in self.dependencies
            ],
            "incidents": [
                {
                    "service": i.service,
                    "type": i.incident_type.value,
                    "timestamp": i.timestamp.isoformat(),
                    "severity": i.severity,
                    "description": i.description,
                    "evidence": i.evidence,
                }
                for i in self.incidents
            ],
        }
