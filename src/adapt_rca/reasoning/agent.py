from typing import List, Dict

def analyze_incident(events: List[Dict]) -> Dict:
    """
    Placeholder for the agentic reasoning logic.

    For now, returns a static structure so the CLI can run end-to-end.
    Later, plug in an LLM here.
    """
    services = sorted({e.get("service") for e in events if e.get("service")})
    return {
        "incident_summary": "Prototype analysis: {} events across services: {}".format(
            len(events), ", ".join(services)
        ),
        "probable_root_causes": [
            "Prototype root cause – plug in LLM or heuristics here."
        ],
        "recommended_actions": [
            "Add real reasoning logic in adapt_rca.reasoning.agent.analyze_incident()."
        ],
    }
