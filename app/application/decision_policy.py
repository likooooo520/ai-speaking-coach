"""将既有介入结果映射为 Agent Decision 的无副作用策略。"""

from typing import Iterable, Optional

from app.domain.decision import AgentAction, AgentDecision
from app.domain.evidence import Evidence
from app.domain.intervention import InterventionDecision, InterventionType
from app.domain.observation import Observation
from app.domain.priority import PriorityResult
from app.domain.task import LearningTask, TaskStatus


class AgentDecisionPolicy:
    """只定义决策协议，不启动动作、不修改任何状态。"""

    def decide(
        self, observation: Optional[Observation], evidence: Optional[Evidence],
        priority: Optional[PriorityResult], intervention: Optional[InterventionDecision], *,
        active_task: Optional[LearningTask] = None, system_error: bool = False,
        active_tasks: Optional[Iterable[LearningTask]] = None,
    ) -> Optional[AgentDecision]:
        if system_error or observation is None or evidence is None:
            return None
        asr_uncertain = bool(evidence.error.asr_uncertain or evidence.naturalness.asr_uncertain)
        if intervention is None:
            return AgentDecision(
                action=AgentAction.CONTINUE, reason="没有可执行的介入结果",
                priority=priority.level if priority else None, asr_uncertain=asr_uncertain,
            )
        candidates = list(active_tasks) if active_tasks is not None else ([active_task] if active_task else [])
        related_task = next((task for task in candidates if self._related_active_task(task, priority)), None)
        if related_task is not None:
            return AgentDecision.from_intervention(
                intervention, priority_result=priority, target_task=related_task,
                action=AgentAction.TASK_FOLLOW_UP, reason="当前问题与已有 Active Task 相关",
                action_hint="围绕已有任务继续当前对话或训练", asr_uncertain=asr_uncertain,
            )
        action = self._action_for(intervention.type)
        return AgentDecision.from_intervention(
            intervention, priority_result=priority, action=action,
            action_hint=self._hint(action),
            requires_user_confirmation=bool(intervention.should_create_task),
            asr_uncertain=asr_uncertain,
        )

    @staticmethod
    def _action_for(kind: InterventionType) -> AgentAction:
        return {
            InterventionType.CONTINUE: AgentAction.CONTINUE,
            InterventionType.LIGHT_FEEDBACK: AgentAction.GENTLE_FEEDBACK,
            InterventionType.INTERRUPT: AgentAction.INTERRUPT,
            InterventionType.TARGETED_PRACTICE: AgentAction.TARGETED_PRACTICE,
            InterventionType.REVIEW_LATER: AgentAction.REVIEW_LATER,
        }[kind]

    @staticmethod
    def _hint(action: AgentAction) -> str:
        return {
            AgentAction.CONTINUE: "继续正常聊天",
            AgentAction.GENTLE_FEEDBACK: "在不打断对话的情况下提供轻量反馈",
            AgentAction.INTERRUPT: "主动处理当前高价值问题",
            AgentAction.TARGETED_PRACTICE: "进入专项训练流程",
            AgentAction.REVIEW_LATER: "记录为 Session Review 候选",
        }[action]

    @staticmethod
    def _related_active_task(task: Optional[LearningTask], priority: Optional[PriorityResult]):
        if task is None or task.status != TaskStatus.ACTIVE or priority is None:
            return None
        target = " ".join(priority.target_key.lower().split())
        task_text = " ".join(f"{task.title} {task.description}".lower().split())
        return task if target and (target in task_text or task_text in target) else None
