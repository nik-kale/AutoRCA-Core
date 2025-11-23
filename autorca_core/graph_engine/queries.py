"""
Graph queries: Helper methods to analyze and traverse the service graph.

Provides utilities to find causal chains, hotspots, and correlation patterns.
"""

from typing import List, Set, Dict, Tuple
from dataclasses import dataclass

from autorca_core.model.graph import ServiceGraph, IncidentNode, Dependency


@dataclass
class CausalChain:
    """
    Represents a potential causal chain of incidents.

    Example: DB latency → API timeouts → Frontend errors
    """
    incidents: List[IncidentNode]
    services: List[str]
    score: float  # Confidence score (0.0 - 1.0)
    explanation: str

    def __str__(self):
        chain = " → ".join(self.services)
        return f"{chain} (score={self.score:.2f})"


class GraphQueries:
    """
    Query and analysis utilities for ServiceGraph.

    Provides methods to find root causes, propagation paths, and correlations.
    """

    def __init__(self, graph: ServiceGraph):
        self.graph = graph

    def find_hotspot_services(self, top_n: int = 5) -> List[Tuple[str, float]]:
        """
        Find services with the most/highest severity incidents (hotspots).

        Args:
            top_n: Return top N services

        Returns:
            List of (service_name, total_severity) tuples, sorted by severity
        """
        severity_map: Dict[str, float] = {}
        for incident in self.graph.incidents:
            severity_map[incident.service] = severity_map.get(incident.service, 0.0) + incident.severity

        sorted_services = sorted(severity_map.items(), key=lambda x: x[1], reverse=True)
        return sorted_services[:top_n]

    def find_root_cause_candidates(self) -> List[str]:
        """
        Find likely root cause services.

        Root causes are typically services that:
        1. Have incidents
        2. Are depended upon by other services with incidents (downstream impact)
        3. Don't depend on services with incidents (not a consequence)

        Returns:
            List of service names sorted by root cause likelihood
        """
        incident_services = {i.service for i in self.graph.incidents}

        candidates: Dict[str, float] = {}

        for service in incident_services:
            score = 0.0

            # Get incidents for this service
            service_incidents = self.graph.get_incidents_for_service(service)
            total_severity = sum(i.severity for i in service_incidents)
            score += total_severity

            # Boost score if downstream services have incidents
            upstream_deps = self.graph.get_upstream_dependencies(service)
            for dep in upstream_deps:
                if dep.from_service in incident_services:
                    score += 0.5  # Bonus for causing downstream issues

            # Penalize if this service depends on services with incidents
            # (likely a consequence, not a root cause)
            downstream_deps = self.graph.get_dependencies_for_service(service)
            for dep in downstream_deps:
                if dep.to_service in incident_services:
                    score -= 0.3  # Penalty for depending on failing services

            candidates[service] = score

        # Sort by score (highest first)
        sorted_candidates = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
        return [service for service, score in sorted_candidates if score > 0]

    def find_causal_chains(self, max_length: int = 5) -> List[CausalChain]:
        """
        Find potential causal chains of incidents.

        A causal chain is a sequence of services where:
        - Each service has an incident
        - There's a dependency path connecting them
        - Incidents occur in temporal order (earlier service causes later)

        Args:
            max_length: Maximum chain length

        Returns:
            List of CausalChain objects, sorted by score
        """
        incident_services = {i.service for i in self.graph.incidents}
        chains: List[CausalChain] = []

        # For each service with incidents, try to build chains
        for root_service in incident_services:
            self._explore_chains(
                current_path=[root_service],
                visited=set([root_service]),
                chains=chains,
                max_length=max_length,
            )

        # Score and sort chains
        for chain in chains:
            chain.score = self._score_chain(chain)

        return sorted(chains, key=lambda c: c.score, reverse=True)

    def get_incident_timeline(self) -> List[IncidentNode]:
        """
        Get all incidents sorted by timestamp (earliest first).

        Useful for understanding the temporal sequence of events.
        """
        return sorted(self.graph.incidents, key=lambda i: i.timestamp)

    def get_services_with_recent_changes(self) -> List[str]:
        """
        Get services that have recent config/deployment changes.

        These are potential root causes since changes often cause incidents.
        """
        from autorca_core.model.graph import IncidentType

        change_types = {IncidentType.CONFIG_CHANGE, IncidentType.DEPLOYMENT}
        services_with_changes = set()

        for incident in self.graph.incidents:
            if incident.incident_type in change_types:
                services_with_changes.add(incident.service)

        return list(services_with_changes)

    def _explore_chains(
        self,
        current_path: List[str],
        visited: Set[str],
        chains: List[CausalChain],
        max_length: int,
    ) -> None:
        """
        Recursively explore dependency graph to find causal chains.

        Uses DFS to traverse from a root service to downstream dependent services.
        """
        if len(current_path) >= max_length:
            return

        current_service = current_path[-1]

        # Find services that depend on current_service (upstream dependencies)
        upstream_deps = self.graph.get_upstream_dependencies(current_service)

        for dep in upstream_deps:
            next_service = dep.from_service

            # Skip if already visited or no incidents
            if next_service in visited:
                continue

            incidents_for_next = self.graph.get_incidents_for_service(next_service)
            if not incidents_for_next:
                continue

            # Add to path
            new_path = current_path + [next_service]
            new_visited = visited | {next_service}

            # Create a chain if path length >= 2
            if len(new_path) >= 2:
                # Collect incidents for all services in the chain
                chain_incidents = []
                for service in new_path:
                    chain_incidents.extend(self.graph.get_incidents_for_service(service))

                explanation = self._generate_chain_explanation(new_path)
                chains.append(CausalChain(
                    incidents=chain_incidents,
                    services=new_path,
                    score=0.0,  # Will be scored later
                    explanation=explanation,
                ))

            # Continue exploration
            self._explore_chains(new_path, new_visited, chains, max_length)

    def _score_chain(self, chain: CausalChain) -> float:
        """
        Score a causal chain based on:
        - Total severity of incidents
        - Temporal ordering (earlier incidents likely cause later ones)
        - Chain length (longer chains are less likely)
        """
        score = 0.0

        # Base score: sum of incident severities
        total_severity = sum(i.severity for i in chain.incidents)
        score += total_severity

        # Bonus for temporal ordering
        incidents_by_service = {i.service: i for i in chain.incidents}
        properly_ordered = True
        for i in range(len(chain.services) - 1):
            service_a = chain.services[i]
            service_b = chain.services[i + 1]

            if service_a in incidents_by_service and service_b in incidents_by_service:
                incident_a = incidents_by_service[service_a]
                incident_b = incidents_by_service[service_b]

                # A should happen before or around the same time as B
                if incident_a.timestamp > incident_b.timestamp:
                    properly_ordered = False
                    break

        if properly_ordered:
            score += 0.5

        # Penalty for long chains (less likely)
        chain_length_penalty = (len(chain.services) - 2) * 0.1
        score -= chain_length_penalty

        return max(0.0, score)

    def _generate_chain_explanation(self, services: List[str]) -> str:
        """Generate a human-readable explanation of a causal chain."""
        if len(services) == 2:
            return f"Incident in {services[0]} likely caused issues in {services[1]}"
        else:
            chain_str = " → ".join(services)
            return f"Propagation chain: {chain_str}"
