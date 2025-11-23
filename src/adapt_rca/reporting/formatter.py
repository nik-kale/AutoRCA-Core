from typing import Dict

def format_human_readable(result: Dict) -> str:
    lines = []
    lines.append("# Incident Analysis")
    lines.append("")
    lines.append(f"Summary: {result.get('incident_summary')}")
    lines.append("")
    lines.append("Probable root causes:")
    for rc in result.get("probable_root_causes", []):
        lines.append(f"- {rc}")
    lines.append("")
    lines.append("Recommended actions:")
    for action in result.get("recommended_actions", []):
        lines.append(f"- {action}")
    return "\n".join(lines)
