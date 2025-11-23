"""
Rule-based RCA heuristics.

Simple, deterministic rules for identifying root causes without requiring an LLM.
"""

from typing import List, Dict, Set
from dataclasses import dataclass
from datetime import timedelta

from autorca_core.model.graph import ServiceGraph, IncidentNode, IncidentType
from autorca_core.graph_engine.queries import GraphQueries, CausalChain


@dataclass
class RootCauseCandidate:
    """
    A potential root cause identified by rules or LLM.

    Attributes:
        service: Service where the root cause is located
        incident_type: Type of incident (error spike, latency, etc.)
        confidence: Confidence score (0.0 - 1.0)
        explanation: Human-readable explanation
        evidence: Supporting evidence (log lines, metrics, etc.)
        remediation: Suggested remediation steps
    """
    service: str
    incident_type: IncidentType
    confidence: float
    explanation: str
    evidence: List[str]
    remediation: List[str]

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "service": self.service,
            "incident_type": self.incident_type.value,
            "confidence": self.confidence,
            "explanation": self.explanation,
            "evidence": self.evidence,
            "remediation": self.remediation,
        }


def apply_rules(graph: ServiceGraph) -> List[RootCauseCandidate]:
    """
    Apply rule-based heuristics to identify root cause candidates.

    Rules applied:
    1. Recent deployment/config changes are strong root cause candidates
    2. Services with high incident severity are candidates
    3. Leaf services with errors (no downstream dependencies with errors) are candidates
    4. Services with resource exhaustion are strong candidates
    5. Causal chains identify propagation patterns

    Args:
        graph: ServiceGraph with incidents and dependencies

    Returns:
        List of RootCauseCandidate objects, sorted by confidence (highest first)
    """
    candidates: List[RootCauseCandidate] = []
    queries = GraphQueries(graph)

    # Rule 1: Recent deployments/config changes
    candidates.extend(_rule_recent_changes(graph, queries))

    # Rule 2: Resource exhaustion
    candidates.extend(_rule_resource_exhaustion(graph, queries))

    # Rule 3: Leaf service errors (no downstream dependencies with errors)
    candidates.extend(_rule_leaf_errors(graph, queries))

    # Rule 4: Error spikes in foundational services (e.g., databases)
    candidates.extend(_rule_foundational_services(graph, queries))

    # Rule 5: Causal chain analysis
    candidates.extend(_rule_causal_chains(graph, queries))

    # Sort by confidence (highest first)
    candidates.sort(key=lambda c: c.confidence, reverse=True)

    return candidates


def _rule_recent_changes(graph: ServiceGraph, queries: GraphQueries) -> List[RootCauseCandidate]:
    """
    Rule: Services with recent deployments or config changes are strong root cause candidates.
    """
    candidates = []
    services_with_changes = queries.get_services_with_recent_changes()

    for service in services_with_changes:
        # Get all incidents for this service
        incidents = graph.get_incidents_for_service(service)

        # Find deployment/config change incidents
        change_incidents = [
            i for i in incidents
            if i.incident_type in (IncidentType.DEPLOYMENT, IncidentType.CONFIG_CHANGE)
        ]

        if not change_incidents:
            continue

        # Get other (non-change) incidents
        other_incidents = [
            i for i in incidents
            if i.incident_type not in (IncidentType.DEPLOYMENT, IncidentType.CONFIG_CHANGE)
        ]

        # Check if other incidents occurred shortly after the change
        for change in change_incidents:
            nearby_incidents = [
                i for i in other_incidents
                if abs((i.timestamp - change.timestamp).total_seconds()) < 600  # Within 10 minutes
            ]

            if nearby_incidents:
                evidence = [change.description] + [i.description for i in nearby_incidents[:3]]
                candidates.append(RootCauseCandidate(
                    service=service,
                    incident_type=change.incident_type,
                    confidence=0.9,
                    explanation=f"Recent {change.incident_type.value} in {service} followed by errors",
                    evidence=evidence,
                    remediation=[
                        f"Review recent {change.incident_type.value} in {service}",
                        f"Consider rolling back to previous version",
                        "Check deployment logs and config diffs",
                    ],
                ))
                break  # Only create one candidate per service

    return candidates


def _rule_resource_exhaustion(graph: ServiceGraph, queries: GraphQueries) -> List[RootCauseCandidate]:
    """
    Rule: Services with resource exhaustion (CPU, memory, connections) are strong candidates.
    """
    candidates = []

    for incident in graph.incidents:
        if incident.incident_type == IncidentType.RESOURCE_EXHAUSTION:
            candidates.append(RootCauseCandidate(
                service=incident.service,
                incident_type=incident.incident_type,
                confidence=0.85,
                explanation=f"Resource exhaustion in {incident.service}: {incident.description}",
                evidence=incident.evidence,
                remediation=[
                    f"Scale up {incident.service} resources (CPU, memory, connections)",
                    "Check for resource leaks or inefficient queries",
                    "Review recent traffic patterns and scaling policies",
                ],
            ))

    return candidates


def _rule_leaf_errors(graph: ServiceGraph, queries: GraphQueries) -> List[RootCauseCandidate]:
    """
    Rule: Services with errors that don't depend on other failing services are likely root causes.
    """
    candidates = []
    incident_services = {i.service for i in graph.incidents}

    for service in incident_services:
        # Get dependencies for this service
        deps = graph.get_dependencies_for_service(service)

        # Check if any dependencies have incidents
        has_failing_dependencies = any(dep.to_service in incident_services for dep in deps)

        if not has_failing_dependencies:
            # This is a leaf service with errors - strong root cause candidate
            service_incidents = graph.get_incidents_for_service(service)
            error_incidents = [
                i for i in service_incidents
                if i.incident_type in (IncidentType.ERROR_SPIKE, IncidentType.LATENCY_SPIKE)
            ]

            if error_incidents:
                incident = error_incidents[0]  # Use the first/most severe
                candidates.append(RootCauseCandidate(
                    service=service,
                    incident_type=incident.incident_type,
                    confidence=0.75,
                    explanation=f"{service} has errors with no failing dependencies",
                    evidence=incident.evidence,
                    remediation=[
                        f"Investigate internal errors in {service}",
                        "Check application logs for exceptions and stack traces",
                        "Review recent code changes or deployments",
                    ],
                ))

    return candidates


def _rule_foundational_services(graph: ServiceGraph, queries: GraphQueries) -> List[RootCauseCandidate]:
    """
    Rule: Errors in foundational services (databases, caches) that many services depend on
    are likely root causes.
    """
    candidates = []

    # Find services with many upstream dependencies (many services depend on them)
    dependency_counts: Dict[str, int] = {}
    for dep in graph.dependencies:
        dependency_counts[dep.to_service] = dependency_counts.get(dep.to_service, 0) + 1

    # Services with 2+ dependents are considered foundational
    foundational_services = {service for service, count in dependency_counts.items() if count >= 2}

    for service in foundational_services:
        incidents = graph.get_incidents_for_service(service)
        if incidents:
            incident = incidents[0]  # Use the first/most severe
            candidates.append(RootCauseCandidate(
                service=service,
                incident_type=incident.incident_type,
                confidence=0.8,
                explanation=f"{service} is a foundational service with incidents affecting multiple dependents",
                evidence=incident.evidence,
                remediation=[
                    f"Investigate {service} - it's a critical dependency",
                    "Check for database/cache connection issues or saturation",
                    "Review query performance and connection pooling",
                ],
            ))

    return candidates


def _rule_causal_chains(graph: ServiceGraph, queries: GraphQueries) -> List[RootCauseCandidate]:
    """
    Rule: Analyze causal chains to identify the root (earliest) service in the chain.
    """
    candidates = []
    chains = queries.find_causal_chains(max_length=4)

    # Take the top 3 most confident chains
    for chain in chains[:3]:
        if chain.score < 0.5:  # Skip low-confidence chains
            continue

        # The root cause is the first service in the chain
        root_service = chain.services[0]
        root_incidents = [i for i in chain.incidents if i.service == root_service]

        if root_incidents:
            incident = root_incidents[0]
            candidates.append(RootCauseCandidate(
                service=root_service,
                incident_type=incident.incident_type,
                confidence=min(0.7, chain.score),  # Cap at 0.7 for chain-based inference
                explanation=f"Root of causal chain: {chain.explanation}",
                evidence=incident.evidence,
                remediation=[
                    f"Fix issues in {root_service} to resolve downstream failures",
                    f"Causal chain: {' → '.join(chain.services)}",
                ],
            ))

    return candidates
