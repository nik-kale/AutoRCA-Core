from typing import Dict

def normalize_event(raw: Dict) -> Dict:
    """
    Normalizes a raw log record into a common event schema.
    This is intentionally simple as a starting point.
    """
    return {
        "timestamp": raw.get("timestamp"),
        "service": raw.get("service") or raw.get("component"),
        "level": raw.get("level") or raw.get("severity"),
        "message": raw.get("message"),
        "raw": raw,
    }
