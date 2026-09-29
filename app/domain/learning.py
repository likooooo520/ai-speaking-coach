from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class LearningEventType(str, Enum):
    ERROR_DETECTED = "error_detected"
    NATURALNESS_OBSERVED = "naturalness_observed"
    PERFORMANCE_RECORDED = "performance_recorded"
    PRACTICE_STARTED = "practice_started"
    PRACTICE_COMPLETED = "practice_completed"
    SESSION_COMPLETED = "session_completed"


class LearningEvent(BaseModel):
    """学习事件的数据表示，不负责触发任何副作用。"""

    type: LearningEventType
    session_id: Optional[str] = None
    turn_id: Optional[int] = None
    original: Optional[str] = None
    better: Optional[str] = None
    alternatives: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None
    practice_type: Optional[str] = None
    focus: Optional[Dict[str, Any]] = None
    performance: Optional[Dict[str, Any]] = None
