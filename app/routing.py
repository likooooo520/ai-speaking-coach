from dataclasses import dataclass


@dataclass
class RoutingDecision:

    action: str

    reason: str

    target_phase: str | None = None


class SessionRouter:

    def decide(
        self,
        current_phase,
        performance_band,
        repeated_error_count=0,
        naturalness_count=0,
        remaining_minutes=0,
        turn_count=0,
        current_error_detected=False,
        current_naturalness_detected=False,
        current_error=None,
        matched_historical_error=None,
        current_error_frequency=0,
        matched_historical_naturalness=None,
        current_naturalness_frequency=0
    ):

        # ========================================
        # Session 即将结束
        # ========================================

        if remaining_minutes <= 5:

            if current_phase != "review":

                return RoutingDecision(
                    action="move_to_review",
                    reason=(
                        "The session is almost finished."
                    ),
                    target_phase="review"
                )

        # ========================================
        # Warm-up
        # ========================================

        if current_phase == "warmup":

            # 至少进行 2 轮再考虑离开 Warm-up
            if turn_count < 2:

                return RoutingDecision(
                    action="continue",
                    reason=(
                        "Warm-up needs at least "
                        "two speaking turns."
                    )
                )

            # 表现很弱，继续热身
            if performance_band == "weak":

                return RoutingDecision(
                    action="continue",
                    reason=(
                        "The learner needs more "
                        "warm-up and confidence building."
                    )
                )

            # 正常或强表现，提前进入主对话
            return RoutingDecision(
                action="move_to_conversation",
                reason=(
                    "Warm-up has collected enough evidence "
                    "and the learner is ready for the main "
                    "conversation."
                ),
                target_phase="main_conversation"
            )

        # ========================================
        # Main Conversation
        # ========================================

        if current_phase == "main_conversation":

            # 只有当前这一轮真的出现重复问题，
            # 才进入 Targeted Practice。
            if (
                current_error_detected
                and matched_historical_error is not None
                and current_error_frequency >= 2
            ):

                return RoutingDecision(
                    action="move_to_targeted_practice",
                    reason=(
                        "A recurring error is relevant "
                        "to the current conversation."
                    ),
                    target_phase="targeted_practice"
                )

            if (
                current_naturalness_detected
                and matched_historical_naturalness is not None
                and current_naturalness_frequency >= 3
            ):
                return RoutingDecision(
                    action="move_to_targeted_practice",
                    reason=(
                        "A recurring naturalness pattern is "
                        "relevant to the current conversation."
                    ),
                    target_phase="targeted_practice"
                )

            # 当前表现优秀，且还有足够时间挑战
            if (
                performance_band == "strong"
                and remaining_minutes > 12
            ):

                return RoutingDecision(
                    action="move_to_challenge",
                    reason=(
                        "The learner is performing strongly "
                        "and is ready for a greater challenge."
                    ),
                    target_phase="challenge"
                )

            return RoutingDecision(
                action="continue",
                reason=(
                    "Continue natural conversation."
                )
            )

        # ========================================
        # Challenge
        # ========================================

        if current_phase == "challenge":

            if performance_band == "weak":

                return RoutingDecision(
                    action="return_to_conversation",
                    reason=(
                        "The challenge is currently "
                        "too difficult."
                    ),
                    target_phase="main_conversation"
                )

            return RoutingDecision(
                action="continue",
                reason=(
                    "Continue the speaking challenge."
                )
            )

        if current_phase == "deep_discussion":
            if performance_band == "weak":
                return RoutingDecision(
                    action="return_to_conversation",
                    reason="Deep discussion is currently too difficult.",
                    target_phase="main_conversation"
                )
            if performance_band == "strong":
                return RoutingDecision(
                    action="move_to_challenge",
                    reason="The learner is ready for a speaking challenge.",
                    target_phase="challenge"
                )
            return RoutingDecision(
                action="continue",
                reason="Continue building nuanced discussion."
            )

        # ========================================
        # Targeted Practice
        # ========================================

        if current_phase == "targeted_practice":

            return RoutingDecision(
                action="continue",
                reason=(
                    "Continue focused practice "
                    "on the learner's current weakness."
                )
            )

        # ========================================
        # Review
        # ========================================

        if current_phase == "review":

            return RoutingDecision(
                action="continue",
                reason=(
                    "Review the most important "
                    "improvements from this session."
                )
            )

        # ========================================
        # Default
        # ========================================

        return RoutingDecision(
            action="continue",
            reason="No routing change required."
        )
