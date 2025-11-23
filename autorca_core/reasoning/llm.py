"""
LLM interface for RCA summarization and reasoning.

Provides an abstraction for calling LLMs to enhance rule-based RCA with
natural language explanations and insights.
"""

from typing import List, Dict, Any, Optional, Protocol
from dataclasses import dataclass

from autorca_core.model.graph import ServiceGraph
from autorca_core.reasoning.rules import RootCauseCandidate


class LLMInterface(Protocol):
    """
    Protocol for LLM integrations.

    Implementations can use OpenAI, Anthropic, local models, etc.
    """

    def summarize_rca(
        self,
        graph: ServiceGraph,
        candidates: List[RootCauseCandidate],
        primary_symptom: str,
    ) -> str:
        """
        Generate a natural language summary of the RCA.

        Args:
            graph: ServiceGraph with incidents and dependencies
            candidates: Root cause candidates from rules
            primary_symptom: The primary symptom reported by the user

        Returns:
            Human-readable RCA summary
        """
        ...

    def enhance_remediation(
        self,
        candidate: RootCauseCandidate,
        context: Dict[str, Any],
    ) -> List[str]:
        """
        Enhance remediation suggestions with LLM insights.

        Args:
            candidate: Root cause candidate
            context: Additional context (logs, metrics, etc.)

        Returns:
            List of enhanced remediation steps
        """
        ...


class DummyLLM:
    """
    Dummy LLM implementation for testing and offline use.

    Returns simple templated responses without calling an actual LLM.
    """

    def summarize_rca(
        self,
        graph: ServiceGraph,
        candidates: List[RootCauseCandidate],
        primary_symptom: str,
    ) -> str:
        """Generate a simple templated summary."""
        if not candidates:
            return f"No root cause candidates identified for: {primary_symptom}"

        top_candidate = candidates[0]

        summary_parts = [
            f"## RCA Summary: {primary_symptom}",
            "",
            f"**Most Likely Root Cause:** {top_candidate.service} ({top_candidate.incident_type.value})",
            f"**Confidence:** {top_candidate.confidence:.0%}",
            "",
            f"**Explanation:** {top_candidate.explanation}",
            "",
            "**Evidence:**",
        ]

        for i, evidence in enumerate(top_candidate.evidence[:5], 1):
            summary_parts.append(f"{i}. {evidence}")

        summary_parts.append("")
        summary_parts.append("**Recommended Actions:**")

        for i, action in enumerate(top_candidate.remediation, 1):
            summary_parts.append(f"{i}. {action}")

        # Add other candidates if available
        if len(candidates) > 1:
            summary_parts.append("")
            summary_parts.append("**Other Possible Causes:**")
            for candidate in candidates[1:4]:  # Show up to 3 more
                summary_parts.append(
                    f"- {candidate.service}: {candidate.explanation} (confidence: {candidate.confidence:.0%})"
                )

        return "\n".join(summary_parts)

    def enhance_remediation(
        self,
        candidate: RootCauseCandidate,
        context: Dict[str, Any],
    ) -> List[str]:
        """Return the original remediation steps (no enhancement)."""
        return candidate.remediation


# TODO: Implement OpenAI, Anthropic, or local LLM integrations
class OpenAILLM:
    """
    OpenAI LLM integration.

    TODO: Implement using OpenAI API for production use.
    """

    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.api_key = api_key
        self.model = model
        # TODO: Initialize OpenAI client

    def summarize_rca(
        self,
        graph: ServiceGraph,
        candidates: List[RootCauseCandidate],
        primary_symptom: str,
    ) -> str:
        """
        TODO: Call OpenAI API to generate RCA summary.

        Prompt should include:
        - Primary symptom
        - Service graph structure
        - Incident timeline
        - Top root cause candidates with evidence
        """
        raise NotImplementedError("OpenAI integration not yet implemented")

    def enhance_remediation(
        self,
        candidate: RootCauseCandidate,
        context: Dict[str, Any],
    ) -> List[str]:
        """
        TODO: Call OpenAI API to enhance remediation steps.
        """
        raise NotImplementedError("OpenAI integration not yet implemented")


class AnthropicLLM:
    """
    Anthropic Claude LLM integration.

    TODO: Implement using Anthropic API for production use.
    """

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key
        self.model = model
        # TODO: Initialize Anthropic client

    def summarize_rca(
        self,
        graph: ServiceGraph,
        candidates: List[RootCauseCandidate],
        primary_symptom: str,
    ) -> str:
        """
        TODO: Call Anthropic API to generate RCA summary.
        """
        raise NotImplementedError("Anthropic integration not yet implemented")

    def enhance_remediation(
        self,
        candidate: RootCauseCandidate,
        context: Dict[str, Any],
    ) -> List[str]:
        """
        TODO: Call Anthropic API to enhance remediation steps.
        """
        raise NotImplementedError("Anthropic integration not yet implemented")
