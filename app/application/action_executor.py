"""将 AgentDecision 转换为最小、可审计的 ActionResult。"""

from typing import Any, Callable, Optional

from app.domain.action import ActionResult
from app.domain.decision import AgentAction, AgentDecision


class ActionExecutor:
    """执行已确定的 Action，不重新进行任何 Agent 决策。"""

    def __init__(self, *, targeted_practice_handler: Optional[Callable[[AgentDecision], Any]] = None):
        self.targeted_practice_handler = targeted_practice_handler

    def execute(self, decision: AgentDecision) -> ActionResult:
        if self._is_system_error(decision):
            return self._result(decision, True, "system error / turn unavailable", "安全结束本次执行")

        if decision.action == AgentAction.CONTINUE:
            return self._result(decision, True, decision.reason, "继续正常聊天")
        if decision.action == AgentAction.GENTLE_FEEDBACK:
            return self._result(decision, True, decision.reason, decision.action_hint)
        if decision.action == AgentAction.INTERRUPT:
            return self._result(decision, True, decision.reason, decision.action_hint)
        if decision.action == AgentAction.REVIEW_LATER:
            return self._result(decision, True, decision.reason, "保留给 Session Review")
        if decision.action == AgentAction.TASK_FOLLOW_UP:
            return self._result(decision, True, decision.reason, "围绕已有 Active Task 继续", next_step=decision.action_hint)
        if decision.action == AgentAction.TARGETED_PRACTICE:
            return self._execute_targeted_practice(decision)
        return self._result(decision, False, "unsupported action", None)

    def _execute_targeted_practice(self, decision: AgentDecision) -> ActionResult:
        if self.targeted_practice_handler is None:
            return self._result(
                decision, False,
                "targeted practice execution interface not available", None,
            )
        try:
            output = self.targeted_practice_handler(decision)
        except Exception as exc:  # 执行依赖失败时不得伪造成功
            return self._result(decision, False, f"targeted practice execution failed: {exc}", None)
        if not output:
            return self._result(decision, False, "targeted practice has no valid session focus", None)
        return self._result(decision, True, "targeted practice execution requested", output)

    @staticmethod
    def _result(decision, executed, reason, output, next_step=None):
        return ActionResult(
            action=decision.action,
            executed=executed,
            reason=reason,
            output=output,
            target_task=decision.target_task,
            evidence_references=list(decision.evidence_references),
            next_step=next_step,
        )

    @staticmethod
    def _is_system_error(decision):
        reason = decision.reason.lower()
        return "system error" in reason or "turn unavailable" in reason
