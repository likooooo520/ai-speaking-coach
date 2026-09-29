"""Agent Decision 的纯数据契约。"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from app.domain.intervention import InterventionDecision
from app.domain.priority import PriorityLevel, PriorityResult
from app.domain.task import LearningTask


class AgentAction(str, Enum):
    CONTINUE = "continue"
    GENTLE_FEEDBACK = "gentle_feedback"
    INTERRUPT = "interrupt"
    TARGETED_PRACTICE = "targeted_practice"
    TASK_FOLLOW_UP = "task_follow_up"
    REVIEW_LATER = "review_later"


class AgentDecision(BaseModel):
    """描述 Agent 此刻应该采取什么行动，不执行该行动。"""

    action: AgentAction
    reason: str
    priority: Optional[PriorityLevel] = PriorityLevel.LOW
    intervention: Optional[InterventionDecision] = None
    target_task: Optional[LearningTask] = None
    evidence_references: List[str] = Field(default_factory=list)
    action_hint: Optional[str] = None
    requires_user_confirmation: bool = False
    asr_uncertain: bool = False

    @classmethod
    def from_intervention(
        cls, intervention: InterventionDecision, *,
        priority_result: Optional[PriorityResult] = None,
        target_task: Optional[LearningTask] = None,
        action: AgentAction, reason: Optional[str] = None,
        action_hint: Optional[str] = None,
        requires_user_confirmation: bool = False,
        asr_uncertain: bool = False,
    ) -> "AgentDecision":
        return cls(
            action=action,
            reason=reason or intervention.reason,
            priority=priority_result.level if priority_result else intervention.priority,
            intervention=intervention,
            target_task=target_task,
            evidence_references=list(intervention.evidence),
            action_hint=action_hint,
            requires_user_confirmation=requires_user_confirmation,
            asr_uncertain=asr_uncertain,
        )
