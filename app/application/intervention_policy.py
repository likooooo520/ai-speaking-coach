from typing import Any, Iterable, Mapping, Optional

from app.domain.intervention import InterventionDecision, InterventionType
from app.domain.observation import Observation
from app.domain.evidence import Evidence
from app.domain.priority import PriorityLevel, PriorityResult


class InterventionPolicy:
    """根据学习价值和当前身份决定是否介入；纯函数式，不修改任何状态。"""

    MODES = {"foreign_friend", "teacher", "business_coach"}

    def decide(self, observation: Observation, evidence: Evidence,
               priority: Optional[PriorityResult], mode: str = "foreign_friend",
               session_context: Any = None, recently_practiced: Optional[bool] = None,
               in_targeted_practice: Optional[bool] = None) -> InterventionDecision:
        mode = self._mode(mode)
        context = self._context(session_context)
        item = self._target_evidence(evidence, priority)
        # 同一事实可能来自显式入参、Session 上下文或 Evidence。PriorityEngine 读取的是
        # Evidence，这里必须按同样顺序回退，否则「刚练过」的守卫会整条失效。
        practiced = self._resolve(recently_practiced, context, "recently_practiced", item)
        active = self._resolve(in_targeted_practice, context, "in_targeted_practice", None)
        if not observation.is_valid or priority is None:
            return self._decision(InterventionType.CONTINUE, "没有可执行的英语学习信号", priority, mode)
        if getattr(item, "asr_uncertain", False) or context.get("system_error", False):
            return self._decision(InterventionType.CONTINUE, "信号不确定，暂不将其视为英语错误", priority, mode)
        requested = getattr(item, "user_requested", False) is True
        impact = self._impact(context, priority)
        repeated = getattr(item, "historical_frequency", 0) >= 3
        if active or practiced:
            return self._decision(InterventionType.REVIEW_LATER, "当前任务已覆盖或刚练习过该问题", priority, mode)
        if requested:
            return self._decision(InterventionType.TARGETED_PRACTICE, "用户主动提出学习需求", priority, mode, True, "满足用户明确的专项训练意图")
        if impact:
            return self._decision(InterventionType.INTERRUPT, "问题可能造成沟通误解或关键信息不清", priority, mode)
        if repeated and priority.target_type == "naturalness":
            if mode == "teacher" and priority.level == PriorityLevel.HIGH:
                return self._decision(InterventionType.TARGETED_PRACTICE, "高频自然表达模式值得扩展练习", priority, mode, True, "为重复表达提供替代表达练习")
            return self._decision(InterventionType.REVIEW_LATER, "自然表达模式重复出现，但不应破坏对话", priority, mode)
        if repeated and mode != "foreign_friend":
            return self._decision(InterventionType.INTERRUPT if mode == "teacher" else InterventionType.LIGHT_FEEDBACK, "同一问题已在本次会话重复出现", priority, mode)
        if mode == "teacher" and priority.level == PriorityLevel.HIGH:
            return self._decision(InterventionType.LIGHT_FEEDBACK, "教学模式允许对高价值问题给出轻量反馈", priority, mode)
        if mode == "business_coach" and context.get("professional_relevance", False):
            return self._decision(InterventionType.LIGHT_FEEDBACK, "该表达与商务沟通相关", priority, mode)
        return self._decision(InterventionType.CONTINUE, "普通问题不应打断自然交流", priority, mode)

    def _decision(self, kind, reason, priority, mode, task=False, task_reason=None):
        return InterventionDecision(type=kind, reason=reason, priority=priority.level if priority else PriorityLevel.LOW,
                                    evidence=priority.reasons if priority else [], mode=mode,
                                    should_create_task=task, task_reason=task_reason)

    @staticmethod
    def _target_evidence(evidence: Evidence, priority: Optional[PriorityResult]):
        """取出优先级指向的那一类证据。"""
        if priority is None:
            return None
        return evidence.error if priority.target_type == "error" else evidence.naturalness

    @staticmethod
    def _resolve(explicit, context, key, item):
        """显式入参 > Session 上下文 > Evidence，保证两层看到同一事实。"""
        if explicit is not None:
            return explicit
        if key in context:
            return context[key]
        return getattr(item, key, False) if item is not None else False

    @staticmethod
    def _context(value):
        if isinstance(value, Mapping):
            return dict(value)
        if value is None:
            return {}
        return {name: getattr(value, name) for name in ("communication_impact", "professional_relevance", "recently_practiced", "in_targeted_practice", "system_error") if hasattr(value, name)}

    @staticmethod
    def _impact(context, priority):
        return bool(context.get("communication_impact", False) or "communication_impact" in priority.reasons or "communication_breakdown" in priority.reasons)

    @classmethod
    def _mode(cls, mode):
        value = str(mode or "foreign_friend").lower().replace(" ", "_")
        return value if value in cls.MODES else "foreign_friend"
