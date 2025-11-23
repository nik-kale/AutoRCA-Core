import os
from dataclasses import dataclass

@dataclass
class RCAConfig:
    llm_provider: str = os.getenv("ADAPT_RCA_LLM_PROVIDER", "none")
    llm_model: str = os.getenv("ADAPT_RCA_LLM_MODEL", "")
    max_events: int = int(os.getenv("ADAPT_RCA_MAX_EVENTS", "5000"))
    time_window_minutes: int = int(os.getenv("ADAPT_RCA_TIME_WINDOW", "15"))
