from typing import Iterable, Optional

from app.domain.intervention import InterventionDecision, InterventionType, SessionReview
from app.domain.priority import PriorityLevel


class SessionReviewGenerator:
    """从已产生的决策生成有限、可行动的会话复盘建议。"""

    def generate(self, decisions: Iterable[InterventionDecision], remaining_tasks: Optional[Iterable[dict]] = None) -> SessionReview:
        decisions = list(decisions)
        review = SessionReview()
        for decision in decisions:
            item = {"reason": decision.reason, "priority": decision.priority.value, "evidence": decision.evidence}
            if decision.priority == PriorityLevel.LOW and not decision.should_create_task:
                continue
            review.notable_issues.append(item)
            if decision.should_create_task:
                review.recommended_short_term_tasks.append(item)
            if decision.type == InterventionType.REVIEW_LATER:
                review.repeated_patterns.append(item)
            if "communication" in decision.reason:
                review.communication_issues.append(item)
            if decision.mode == "business_coach":
                review.vocabulary_patterns.append(item)
        review.user_requested_tasks = [x for x in review.recommended_short_term_tasks if "用户主动" in x["reason"]]
        review.recommended_next_session_focus = review.recommended_short_term_tasks[:3]
        tasks = list(remaining_tasks or [])
        high = [task for task in tasks if str(task.get("priority", "")).lower() == "high"]
        if high:
            review.should_offer_extension = True
            review.extension_reason = "仍有未完成的高价值专项训练任务"
        return review

