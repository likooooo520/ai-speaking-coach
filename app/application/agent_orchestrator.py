"""连接 Agent Core 的最小逐 Turn Decision Loop。"""

from typing import Any, Callable, Iterable, Optional

from app.application.action_executor import ActionExecutor
from app.application.decision_policy import AgentDecisionPolicy
from app.application.intervention_policy import InterventionPolicy
from app.application.observation_builder import ObservationBuilder
from app.application.priority_engine import PriorityEngine
from app.domain.decision import AgentAction, AgentDecision
from app.domain.task import LearningTask
from app.domain.turn import TurnResult


class AgentOrchestrator:
    """只协调既有组件，生成 AgentDecision，不执行 Decision。"""

    def __init__(
        self,
        observation_builder: Optional[ObservationBuilder] = None,
        priority_engine: Optional[PriorityEngine] = None,
        intervention_policy: Optional[InterventionPolicy] = None,
        decision_policy: Optional[AgentDecisionPolicy] = None,
        action_executor: Optional[ActionExecutor] = None,
        *,
        task_manager: Any = None,
        active_tasks_provider: Optional[Callable[[], Iterable[LearningTask]]] = None,
    ):
        self.observation_builder = observation_builder or ObservationBuilder()
        self.priority_engine = priority_engine or PriorityEngine()
        self.intervention_policy = intervention_policy or InterventionPolicy()
        self.decision_policy = decision_policy or AgentDecisionPolicy()
        self.action_executor = action_executor or ActionExecutor()
        self.task_manager = task_manager
        self.active_tasks_provider = active_tasks_provider

    def decide(
        self,
        turn_result: TurnResult,
        *,
        mode: str = "foreign_friend",
        session_context: Any = None,
        active_tasks: Optional[Iterable[LearningTask]] = None,
        error_memory: Any = None,
        naturalness_memory: Any = None,
        user_requested: Optional[bool] = None,
        session_relevance: Optional[bool] = None,
        interruption_cost: Optional[int] = None,
    ) -> AgentDecision:
        """按固定顺序分析一个已完成 Turn，并返回纯数据 Decision。"""
        if turn_result.system_error:
            return self._safe_system_error_decision()

        observation, evidence = self.observation_builder.build(
            turn_result,
            error_memory=error_memory,
            naturalness_memory=naturalness_memory,
            user_requested=user_requested,
            session_relevance=session_relevance,
            interruption_cost=interruption_cost,
        )
        if observation is None or evidence is None:
            return self._safe_system_error_decision()

        priority = self.priority_engine.evaluate(observation, evidence, session_context)
        context = self._context(session_context)
        intervention = self.intervention_policy.decide(
            observation, evidence, priority, mode=mode,
            session_context=session_context,
            recently_practiced=context.get("recently_practiced"),
            in_targeted_practice=context.get("in_targeted_practice"),
        )
        decision = self.decision_policy.decide(
            observation, evidence, priority, intervention,
            active_tasks=self._active_tasks(active_tasks),
        )
        return decision or self._safe_system_error_decision()

    def run(self, turn_result: TurnResult, **kwargs):
        """协调一次 Decision 并交给注入的 Executor，不在 Orchestrator 执行动作。"""
        return self.action_executor.execute(self.decide(turn_result, **kwargs))

    def _active_tasks(self, active_tasks):
        if active_tasks is not None:
            return list(active_tasks)
        if self.active_tasks_provider is not None:
            return list(self.active_tasks_provider())
        if self.task_manager is not None:
            repository = getattr(self.task_manager, "repository", None)
            if repository is not None and hasattr(repository, "list"):
                return [task for task in repository.list()
                        if getattr(task.status, "value", task.status) == "active"]
        return []

    @staticmethod
    def _context(value):
        if isinstance(value, dict):
            return value
        if value is None:
            return {}
        return {name: getattr(value, name)
                for name in ("recently_practiced", "in_targeted_practice")
                if hasattr(value, name)}

    @staticmethod
    def _safe_system_error_decision():
        return AgentDecision(
            action=AgentAction.CONTINUE,
            reason="system error / turn unavailable",
            action_hint="保持安全状态，不执行学习介入",
        )
