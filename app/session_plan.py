from dataclasses import dataclass
from typing import List


@dataclass
class PhasePlan:

    name: str

    minutes: int

    description: str


class SessionPlan:

    def __init__(
        self,
        duration_minutes: int
    ):

        if duration_minutes < 5:

            raise ValueError(
                "Session duration must be at least 5 minutes."
            )

        self.duration_minutes = (
            duration_minutes
        )

        self.phases = (
            self._generate_plan()
        )

    # ========================================
    # Generate Plan
    # ========================================

    def _generate_plan(
        self
    ) -> List[PhasePlan]:

        duration = (
            self.duration_minutes
        )

        # ------------------------------------
        # 5-15 minutes
        # ------------------------------------

        if duration <= 15:

            warmup = 2
            review = 2
            targeted = 4

            main = (
                duration
                - warmup
                - targeted
                - review
            )

            return [
                PhasePlan(
                    name="warmup",
                    minutes=warmup,
                    description=(
                        "Easy conversation to get "
                        "into English mode."
                    )
                ),

                PhasePlan(
                    name="main_conversation",
                    minutes=main,
                    description=(
                        "Focused natural conversation "
                        "around the selected topic."
                    )
                ),

                PhasePlan(
                    name="targeted_practice",
                    minutes=targeted,
                    description=(
                        "Practice a recurring error "
                        "or naturalness issue."
                    )
                ),

                PhasePlan(
                    name="review",
                    minutes=review,
                    description=(
                        "Quick review of today's "
                        "key improvements."
                    )
                )
            ]

        # ------------------------------------
        # 16-30 minutes
        # ------------------------------------

        if duration <= 30:

            warmup = 3
            challenge = 4
            targeted = 5
            review = 3

            main = (
                duration
                - warmup
                - challenge
                - targeted
                - review
            )

            return [
                PhasePlan(
                    name="warmup",
                    minutes=warmup,
                    description=(
                        "Warm-up and easy conversation."
                    )
                ),

                PhasePlan(
                    name="main_conversation",
                    minutes=main,
                    description=(
                        "Main natural conversation."
                    )
                ),

                PhasePlan(
                    name="challenge",
                    minutes=challenge,
                    description=(
                        "More demanding speaking tasks."
                    )
                ),

                PhasePlan(
                    name="targeted_practice",
                    minutes=targeted,
                    description=(
                        "Practice a relevant recurring error "
                        "or naturalness pattern."
                    )
                ),

                PhasePlan(
                    name="review",
                    minutes=review,
                    description=(
                        "Review key corrections "
                        "and natural expressions."
                    )
                )
            ]

        # ------------------------------------
        # 31-45 minutes
        # ------------------------------------

        if duration <= 45:

            warmup = 5
            challenge = 8
            practice = 7
            review = 5

            main = (
                duration
                - warmup
                - challenge
                - practice
                - review
            )

            return [
                PhasePlan(
                    name="warmup",
                    minutes=warmup,
                    description=(
                        "Warm-up and conversational entry."
                    )
                ),

                PhasePlan(
                    name="main_conversation",
                    minutes=main,
                    description=(
                        "Natural B2 conversation."
                    )
                ),

                PhasePlan(
                    name="challenge",
                    minutes=challenge,
                    description=(
                        "Push the learner with "
                        "more complex questions."
                    )
                ),

                PhasePlan(
                    name="targeted_practice",
                    minutes=practice,
                    description=(
                        "Practice recurring errors "
                        "and naturalness issues."
                    )
                ),

                PhasePlan(
                    name="review",
                    minutes=review,
                    description=(
                        "Review today's key improvements."
                    )
                )
            ]

        # ------------------------------------
        # 46-60 minutes
        # ------------------------------------

        warmup = 5
        review = 5

        deep_discussion = 10
        challenge = 10
        practice = 10

        main = (
            duration
            - warmup
            - deep_discussion
            - challenge
            - practice
            - review
        )

        if duration <= 60:

            return [
                PhasePlan(
                    name="warmup",
                    minutes=warmup,
                    description=(
                        "Warm-up and conversational entry."
                    )
                ),

                PhasePlan(
                    name="main_conversation",
                    minutes=main,
                    description=(
                        "Extended natural conversation."
                    )
                ),

                PhasePlan(
                    name="deep_discussion",
                    minutes=deep_discussion,
                    description=(
                        "Discuss opinions, reasons, "
                        "examples, and alternative views."
                    )
                ),

                PhasePlan(
                    name="challenge",
                    minutes=challenge,
                    description=(
                        "More demanding spontaneous speaking."
                    )
                ),

                PhasePlan(
                    name="targeted_practice",
                    minutes=practice,
                    description=(
                        "Target recurring errors "
                        "and natural expressions."
                    )
                ),

                PhasePlan(
                    name="review",
                    minutes=review,
                    description=(
                        "Review and repeat "
                        "improved expressions."
                    )
                )
            ]

        # ------------------------------------
        # 60+ minutes
        # ------------------------------------

        remaining = (
            duration
            - 10
        )

        main = round(
            remaining * 0.40
        )

        deep_discussion = round(
            remaining * 0.20
        )

        challenge = round(
            remaining * 0.20
        )

        practice = (
            remaining
            - main
            - deep_discussion
            - challenge
        )

        return [
            PhasePlan(
                name="warmup",
                minutes=5,
                description=(
                    "Warm-up and conversational entry."
                )
            ),

            PhasePlan(
                name="main_conversation",
                minutes=main,
                description=(
                    "Extended natural conversation."
                )
            ),

            PhasePlan(
                name="deep_discussion",
                minutes=deep_discussion,
                description=(
                    "Complex discussion and "
                    "opinion building."
                )
            ),

            PhasePlan(
                name="challenge",
                minutes=challenge,
                description=(
                    "Spontaneous and challenging speaking."
                )
            ),

            PhasePlan(
                name="targeted_practice",
                minutes=practice,
                description=(
                    "Practice recurring weaknesses."
                )
            ),

            PhasePlan(
                name="review",
                minutes=5,
                description=(
                    "Final review and repetition."
                )
            )
        ]

    # ========================================
    # Total
    # ========================================

    def total_minutes(self):

        return sum(
            phase.minutes
            for phase in self.phases
        )

    # ========================================
    # Summary
    # ========================================

    def summary(self):

        return [
            {
                "name": phase.name,
                "minutes": phase.minutes,
                "description": phase.description
            }

            for phase in self.phases
        ]

    # ========================================
    # Print
    # ========================================

    def print_plan(self):

        print()
        print(
            "══════════════════════════════════════"
        )

        print(
            f"       {self.duration_minutes}-Minute Session"
        )

        print(
            "══════════════════════════════════════"
        )

        elapsed = 0

        for index, phase in enumerate(
            self.phases,
            start=1
        ):

            start = elapsed

            end = (
                elapsed
                + phase.minutes
            )

            print()
            print(
                f"{index}. "
                f"{phase.name}"
            )

            print(
                f"   Time: "
                f"{start}-{end} min"
            )

            print(
                f"   Duration: "
                f"{phase.minutes} min"
            )

            print(
                f"   Goal: "
                f"{phase.description}"
            )

            elapsed = end

        print()
        print(
            f"Total: "
            f"{self.total_minutes()} min"
        )

        print(
            "══════════════════════════════════════"
        )
