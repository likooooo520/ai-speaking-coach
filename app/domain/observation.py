from typing import List, Optional

from pydantic import BaseModel, Field

from app.coach import ASRUncertainty, Correction, NaturalnessSuggestion, Performance


class Observation(BaseModel):
    """一次 Turn 中 Agent 观察到的事实。"""

    session_id: str
    turn_id: int
    phase: str
    user_text: str
    correction: Correction = Field(default_factory=Correction)
    naturalness: NaturalnessSuggestion = Field(default_factory=NaturalnessSuggestion)
    asr_uncertainty: List[ASRUncertainty] = Field(default_factory=list)
    performance: Performance = Field(default_factory=Performance)
    topic: Optional[str] = None
    is_valid: bool = True
