"""学习任务领域模型；不依赖 Memory、Session 或具体存储。"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    ACTIVE = "active"
    PRACTICING = "practicing"
    REVIEW = "review"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskSource(str, Enum):
    USER_REQUESTED = "user_requested"
    AGENT_DETECTED = "agent_detected"
    SESSION_REVIEW = "session_review"
    LONG_TERM_GOAL = "long_term_goal"
    COMMUNICATION_ISSUE = "communication_issue"


@dataclass
class LongTermGoal:
    goal_id: str
    title: str
    description: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class LearningTask:
    task_id: str
    title: str
    description: str
    source: TaskSource
    status: TaskStatus
    priority: TaskPriority
    success_criteria: str
    created_at: str
    updated_at: str
    long_term_goal_id: Optional[str] = None
    coach_mode: Optional[str] = None
    related_memory_ids: List[str] = field(default_factory=list)
    related_evidence_ids: List[str] = field(default_factory=list)
    related_observation_ids: List[str] = field(default_factory=list)
    progress: Dict[str, Any] = field(default_factory=dict)
    accepted_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
