from typing import Dict
import json

def export_json(result: Dict, output_path: str) -> None:
    """
    Export analysis results to JSON format.
    """
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

def export_markdown(result: Dict, output_path: str) -> None:
    """
    Export analysis results to Markdown format.
    Placeholder for future implementation.
    """
    lines = []
    lines.append("# Incident Analysis Report")
    lines.append("")
    lines.append(f"## Summary")
    lines.append(result.get('incident_summary', 'N/A'))
    lines.append("")
    lines.append("## Probable Root Causes")
    for rc in result.get("probable_root_causes", []):
        lines.append(f"- {rc}")
    lines.append("")
    lines.append("## Recommended Actions")
    for action in result.get("recommended_actions", []):
        lines.append(f"- {action}")

    with open(output_path, 'w') as f:
        f.write("\n".join(lines))
