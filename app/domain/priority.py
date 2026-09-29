from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class PriorityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


PRIORITY_MEDIUM_THRESHOLD = 0.40
PRIORITY_HIGH_THRESHOLD = 0.70


def priority_level(score: float) -> PriorityLevel:
    if score >= PRIORITY_HIGH_THRESHOLD:
        return PriorityLevel.HIGH
    if score >= PRIORITY_MEDIUM_THRESHOLD:
        return PriorityLevel.MEDIUM
    return PriorityLevel.LOW


class PriorityResult(BaseModel):
    target_type: str
    target_key: str
    score: float = Field(ge=0.0, le=1.0)
    level: PriorityLevel
    reasons: List[str] = Field(default_factory=list)
    confidence: Optional[float] = None

