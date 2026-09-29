"""ActionExecutor 的纯数据结果模型。"""

from typing import Any, List, Optional

from pydantic import BaseModel, Field

from app.domain.decision import AgentAction
from app.domain.task import LearningTask


class ActionResult(BaseModel):
    """描述一次 Action 执行结果，不负责更新学习状态。"""

    action: AgentAction
    executed: bool
    reason: str
    output: Optional[str] = None
    target_task: Optional[LearningTask] = None
    evidence_references: List[str] = Field(default_factory=list)
    next_step: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
