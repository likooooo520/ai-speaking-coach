from typing import Optional

from pydantic import BaseModel, Field


class ErrorEvidence(BaseModel):
    current_error_detected: bool = False
    historical_match: bool = False
    historical_frequency: int = 0
    user_requested: Optional[bool] = None
    asr_uncertain: bool = False
    recently_practiced: Optional[bool] = None


class NaturalnessEvidence(BaseModel):
    current_naturalness_detected: bool = False
    historical_match: bool = False
    historical_frequency: int = 0
    user_requested: Optional[bool] = None
    asr_uncertain: bool = False
    recently_practiced: Optional[bool] = None


class Evidence(BaseModel):
    """支持后续关注的事实依据集合。"""

    error: ErrorEvidence = Field(default_factory=ErrorEvidence)
    naturalness: NaturalnessEvidence = Field(default_factory=NaturalnessEvidence)
    session_relevance: Optional[bool] = None
    interruption_cost: Optional[int] = None
