import time

from app.session import (
    SessionConfig,
    SessionManager
)

from app.routing import (
    SessionRouter
)

from app.targeted_practice import (
    TargetedPracticeManager
)


class AdaptiveSession:

    def __init__(
        self,
        duration_minutes=45
    ):

        config = SessionConfig(
            duration_minutes=duration_minutes
        )

        self.session = SessionManager(
            config
        )

        self.router = SessionRouter()

        self.phase_started_at = None

        self.turn_count = 0

        self.targeted_practice = (
            TargetedPracticeManager()
        )

    # ========================================
    # Start
    # ========================================

    def start(self):

        self.session.start()

        self.phase_started_at = (
            time.time()
        )

        self.turn_count = 0

    # ========================================
    # Status
    # ========================================

    def status(self):

        status = self.session.get_status()

        current_phase = (
            self.session.get_current_phase()
        )

        phase_elapsed = 0

        phase_remaining = 0

        if (
            current_phase is not None
            and self.phase_started_at is not None
        ):

            phase_elapsed = int(
                time.time()
                - self.phase_started_at
            )

            phase_total = (
                current_phase.minutes * 60
            )

            phase_remaining = max(
                0,
                phase_total
                - phase_elapsed
            )

        status[
            "phase_elapsed_seconds"
        ] = phase_elapsed

        status[
            "phase_remaining_seconds"
        ] = phase_remaining

        status[
            "phase_remaining_minutes"
        ] = round(
            phase_remaining / 60,
            1
        )

        status[
            "turn_count"
        ] = self.turn_count

        status[
            "targeted_practice_step"
        ] = (
            self.targeted_practice
            .current_step()
            if self.targeted_practice.has_focus()
            else 0
        )

        return status

    # ========================================
    # Prepare Turn
    # ========================================

    def prepare_turn(self):

        if not self.session.can_continue():

            return self.status()

        status = self.status()

        if (
            status[
                "phase_remaining_seconds"
            ] <= 0
        ):

            next_phase = self.next_phase()

            if next_phase == "completed":

                return self.status()

            return self.status()

        return status

    # ========================================
    # Record Valid Turn
    # ========================================

    def record_turn(self):

        self.turn_count += 1

    # ========================================
    # Start Targeted Practice
    # ========================================

    def start_targeted_practice(
        self,
        decision,
        focus_type="error"
    ):

        if focus_type == "naturalness":
            naturalness = decision.naturalness
            if not naturalness.detected or not naturalness.original:
                return False
            if not naturalness.alternatives:
                return False
            self.targeted_practice.start(
                original=naturalness.original,
                explanation=naturalness.explanation or "",
                category=naturalness.category,
                focus_type="naturalness",
                alternatives=naturalness.alternatives
            )
            return True

        correction = decision.correction

        if not correction.needed:

            return False

        if not correction.original:

            return False

        if not correction.better:

            return False

        self.targeted_practice.start(
            original=correction.original,
            better=correction.better,
            explanation=(
                correction.explanation
                or ""
            ),
            category="error"
            ,focus_type="error"
        )

        return True

    # ========================================
    # Targeted Practice Context
    # ========================================

    def targeted_context(self):

        return (
            self.targeted_practice
            .get_context()
        )

    # ========================================
    # Advance Targeted Practice
    # ========================================

    def advance_targeted_practice(self):

        self.targeted_practice.advance()

        return (
            self.targeted_practice
            .is_completed()
        )

    # ========================================
    # Targeted Practice Completed
    # ========================================

    def targeted_practice_completed(self):

        return (
            self.targeted_practice
            .is_completed()
        )

    # ========================================
    # Available Phases
    # ========================================

    def available_phases(self):

        return [
            phase.name
            for phase in self.session.plan.phases
        ]

    # ========================================
    # Current Phase
    # ========================================

    def current_phase(self):

        return self.session.phase

    # ========================================
    # Route
    # ========================================

    def route(
        self,
        performance_band,
        repeated_error_count=0,
        naturalness_count=0,
        current_error_detected=False,
        current_naturalness_detected=False
        ,current_error=None,
        matched_historical_error=None,
        current_error_frequency=0,
        matched_historical_naturalness=None,
        current_naturalness_frequency=0
    ):

        status = self.status()

        available = (
            self.available_phases()
        )

        decision = self.router.decide(
            current_phase=status[
                "phase"
            ],
            performance_band=performance_band,
            repeated_error_count=(
                repeated_error_count
            ),
            naturalness_count=(
                naturalness_count
            ),
            remaining_minutes=(
                status[
                    "remaining_minutes"
                ]
            ),
            turn_count=self.turn_count,
            current_error_detected=(
                current_error_detected
            ),
            current_naturalness_detected=(
                current_naturalness_detected
            ),
            current_error=current_error,
            matched_historical_error=matched_historical_error,
            current_error_frequency=current_error_frequency,
            matched_historical_naturalness=matched_historical_naturalness,
            current_naturalness_frequency=current_naturalness_frequency
        )

        if decision.target_phase:

            if (
                decision.target_phase
                in available
            ):

                self._move_to_phase(
                    decision.target_phase
                )

            else:

                decision.action = (
                    "continue"
                )

                decision.reason = (
                    "The preferred target phase "
                    "is not available in this "
                    "session plan."
                )

                decision.target_phase = None

        return decision

    # ========================================
    # Move Phase
    # ========================================

    def _move_to_phase(
        self,
        phase
    ):

        self.session.set_phase(
            phase
        )

        self.phase_started_at = (
            time.time()
        )

        if phase != "targeted_practice":

            self.targeted_practice.complete()

    # ========================================
    # Next Phase
    # ========================================

    def next_phase(self):

        next_phase = (
            self.session.next_phase()
        )

        if next_phase == "completed":

            self.phase_started_at = None

            return next_phase

        self.phase_started_at = (
            time.time()
        )

        return next_phase

    # ========================================
    # End
    # ========================================

    def end(self):

        self.session.end()

        self.phase_started_at = None

    # ========================================
    # Continue
    # ========================================

    def can_continue(self):

        return (
            self.session.can_continue()
        )
