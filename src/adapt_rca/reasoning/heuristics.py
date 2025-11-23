from typing import List, Dict

def simple_grouping(events: List[Dict]) -> List[List[Dict]]:
    """
    Very basic grouping: put all events into a single incident candidate.
    Later, this can be replaced with time-window + service-based grouping.
    """
    if not events:
        return []
    return [events]
