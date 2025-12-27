"""
LLM interface for RCA summarization and reasoning.

Provides an abstraction for calling LLMs to enhance rule-based RCA with
natural language explanations and insights.
"""

import os
import time
from typing import List, Dict, Any, Optional, Protocol
from dataclasses import dataclass

from autorca_core.model.graph import ServiceGraph
from autorca_core.reasoning.rules import RootCauseCandidate
from autorca_core.logging import get_logger

logger = get_logger(__name__)


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
    Anthropic Claude LLM integration for RCA summarization.

    Features:
    - Automatic retry with exponential backoff
    - Token usage tracking
    - Cost estimation
    - Error handling with fallback to DummyLLM
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
        max_tokens: int = 2048,
        max_retries: int = 3,
    ):
        """
        Initialize Anthropic LLM client.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Model name to use
            max_tokens: Maximum tokens in response
            max_retries: Maximum number of retry attempts
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.model = model
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.total_tokens_used = 0
        self.total_cost_usd = 0.0

        # Initialize Anthropic client
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError(
                "anthropic package required. Install with: pip install anthropic"
            )

    def summarize_rca(
        self,
        graph: ServiceGraph,
        candidates: List[RootCauseCandidate],
        primary_symptom: str,
    ) -> str:
        """
        Generate an LLM-enhanced RCA summary using Anthropic Claude.

        Args:
            graph: ServiceGraph with incidents and dependencies
            candidates: Root cause candidates from rules
            primary_symptom: The primary symptom reported

        Returns:
            Comprehensive RCA summary with remediation steps
        """
        if not candidates:
            return f"No root cause candidates identified for: {primary_symptom}"

        # Build the analysis context
        user_prompt = self._build_rca_prompt(graph, candidates, primary_symptom)

        # Call Claude API with retry logic
        response_text = self._call_claude_with_retry(user_prompt)

        return response_text

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
            Enhanced remediation steps
        """
        system_prompt = """You are an expert SRE providing remediation guidance.
        Given a root cause and context, provide specific, actionable remediation steps.
        Focus on immediate fixes, verification steps, and prevention strategies."""

        user_prompt = f"""Root Cause: {candidate.service} - {candidate.incident_type.value}

Explanation: {candidate.explanation}

Current Evidence:
{chr(10).join(f"- {e}" for e in candidate.evidence[:5])}

Current Remediation Steps:
{chr(10).join(f"{i}. {step}" for i, step in enumerate(candidate.remediation, 1))}

Please provide enhanced, detailed remediation steps including:
1. Immediate actions to resolve the issue
2. Verification steps to confirm the fix
3. Long-term prevention strategies
4. Monitoring and alerting recommendations

Return the steps as a numbered list."""

        try:
            response_text = self._call_claude_with_retry(
                user_prompt, system_prompt=system_prompt, max_tokens=1024
            )

            # Parse numbered list from response
            lines = response_text.strip().split('\n')
            enhanced_steps = []
            for line in lines:
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-')):
                    # Remove numbering/bullets
                    step = line.lstrip('0123456789.-) ')
                    if step:
                        enhanced_steps.append(step)

            return enhanced_steps if enhanced_steps else candidate.remediation

        except Exception as e:
            logger.warning(f"Failed to enhance remediation: {e}")
            return candidate.remediation

    def _build_rca_prompt(
        self,
        graph: ServiceGraph,
        candidates: List[RootCauseCandidate],
        primary_symptom: str,
    ) -> str:
        """Build the user prompt for RCA summarization."""
        prompt_parts = [
            f"# Root Cause Analysis Request",
            f"",
            f"**Primary Symptom:** {primary_symptom}",
            f"",
            f"## Service Topology",
            f"",
            f"**Services:** {len(graph.services)}",
            f"**Dependencies:** {len(graph.dependencies)}",
            f"**Incidents Detected:** {len(graph.incidents)}",
            f"",
        ]

        # Add service graph structure
        if graph.dependencies:
            prompt_parts.append("**Service Dependencies:**")
            for dep in graph.dependencies[:10]:  # Limit to 10
                prompt_parts.append(f"- {dep.from_service} → {dep.to_service} ({dep.dependency_type.value})")
            prompt_parts.append("")

        # Add incident timeline
        if graph.incidents:
            prompt_parts.append("**Incident Timeline:**")
            sorted_incidents = sorted(graph.incidents, key=lambda i: i.timestamp)
            for incident in sorted_incidents[:15]:  # Limit to 15
                prompt_parts.append(
                    f"- {incident.timestamp.isoformat()}: {incident.service} - "
                    f"{incident.incident_type.value} (severity: {incident.severity:.2f})"
                )
            prompt_parts.append("")

        # Add root cause candidates
        prompt_parts.append("## Root Cause Candidates")
        prompt_parts.append("")

        for i, candidate in enumerate(candidates[:5], 1):  # Top 5
            prompt_parts.append(f"### Candidate {i}: {candidate.service}")
            prompt_parts.append(f"**Type:** {candidate.incident_type.value}")
            prompt_parts.append(f"**Confidence:** {candidate.confidence:.0%}")
            prompt_parts.append(f"**Explanation:** {candidate.explanation}")
            prompt_parts.append("")
            prompt_parts.append("**Evidence:**")
            for evidence in candidate.evidence[:5]:
                prompt_parts.append(f"- {evidence}")
            prompt_parts.append("")
            prompt_parts.append("**Suggested Remediation:**")
            for j, action in enumerate(candidate.remediation, 1):
                prompt_parts.append(f"{j}. {action}")
            prompt_parts.append("")

        return "\n".join(prompt_parts)

    def _call_claude_with_retry(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Call Claude API with exponential backoff retry logic.

        Args:
            user_prompt: User message content
            system_prompt: Optional system prompt
            max_tokens: Optional max tokens override

        Returns:
            Response text from Claude
        """
        if system_prompt is None:
            system_prompt = """You are an expert SRE (Site Reliability Engineer) analyzing a production incident.
Your task is to provide a clear, actionable Root Cause Analysis based on the observability data and detected incidents.

Provide your analysis in the following structure:

## Executive Summary
2-3 sentences summarizing the incident and most likely root cause.

## Root Cause Analysis
Identify the most likely root cause with:
- Confidence level (High/Medium/Low)
- Supporting evidence from the data
- Why this is more likely than other candidates

## Impact Assessment
Describe the scope and severity of the impact.

## Remediation Steps
Provide specific, ordered steps to:
1. Immediately resolve the issue
2. Verify the fix is working
3. Prevent recurrence

## Monitoring Recommendations
What metrics/logs to watch to ensure the issue is resolved and doesn't recur.

Be concise, technical, and actionable. Focus on facts from the data provided."""

        max_tokens = max_tokens or self.max_tokens
        last_error = None

        for attempt in range(self.max_retries):
            try:
                logger.info(f"Calling Anthropic API (attempt {attempt + 1}/{self.max_retries})")

                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )

                # Track token usage
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens
                total_tokens = input_tokens + output_tokens

                self.total_tokens_used += total_tokens

                # Estimate cost (approximate pricing for Claude 3.5 Sonnet)
                # Input: $3/MTok, Output: $15/MTok
                cost = (input_tokens / 1_000_000 * 3.0) + (output_tokens / 1_000_000 * 15.0)
                self.total_cost_usd += cost

                logger.info(
                    f"API call successful. Tokens: {total_tokens} "
                    f"(in: {input_tokens}, out: {output_tokens}), "
                    f"Cost: ${cost:.4f}"
                )

                # Extract text from response
                return response.content[0].text

            except Exception as e:
                last_error = e
                logger.warning(f"API call failed (attempt {attempt + 1}): {e}")

                if attempt < self.max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)

        # All retries failed
        error_msg = f"Failed to call Anthropic API after {self.max_retries} attempts: {last_error}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get token usage and cost statistics.

        Returns:
            Dictionary with usage stats
        """
        return {
            "total_tokens": self.total_tokens_used,
            "total_cost_usd": self.total_cost_usd,
            "model": self.model,
        }
