from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from app.domain.priority import PriorityLevel


class InterventionType(str, Enum):
    CONTINUE = "continue"
    LIGHT_FEEDBACK = "light_feedback"
    INTERRUPT = "interrupt"
    TARGETED_PRACTICE = "targeted_practice"
    REVIEW_LATER = "review_later"


class InterventionDecision(BaseModel):
    type: InterventionType
    reason: str
    priority: PriorityLevel = PriorityLevel.LOW
    evidence: List[str] = Field(default_factory=list)
    mode: str = "foreign_friend"
    should_create_task: bool = False
    task_reason: Optional[str] = None


class SessionReview(BaseModel):
    notable_issues: List[Any] = Field(default_factory=list)
    user_requested_tasks: List[Any] = Field(default_factory=list)
    communication_issues: List[Any] = Field(default_factory=list)
    repeated_patterns: List[Any] = Field(default_factory=list)
    naturalness_patterns: List[Any] = Field(default_factory=list)
    vocabulary_patterns: List[Any] = Field(default_factory=list)
    recommended_short_term_tasks: List[Any] = Field(default_factory=list)
    recommended_next_session_focus: List[Any] = Field(default_factory=list)
    should_offer_extension: bool = False
    extension_reason: Optional[str] = None

