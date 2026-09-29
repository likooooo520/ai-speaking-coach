import time
from dataclasses import dataclass

from app.session_plan import SessionPlan


@dataclass
class SessionConfig:

    duration_minutes: int = 45


class SessionManager:

    def __init__(
        self,
        config=None
    ):

        self.config = (
            config
            or SessionConfig()
        )

        self.plan = SessionPlan(
            self.config.duration_minutes
        )

        self.started_at = None

        self.ended = False

        self.phase = "not_started"

        self.phase_index = -1

        # None = 时间自动控制
        # 具体阶段 = 当前阶段被主动锁定
        self.phase_override = None

    # ========================================
    # Start
    # ========================================

    def start(self):

        self.started_at = time.time()

        self.ended = False

        self.phase_index = 0

        self.phase = (
            self.plan.phases[0].name
        )

        self.phase_override = None

    # ========================================
    # Elapsed
    # ========================================

    def elapsed_seconds(self):

        if self.started_at is None:

            return 0

        return int(
            time.time()
            - self.started_at
        )

    # ========================================
    # Remaining
    # ========================================

    def remaining_seconds(self):

        if self.ended:

            return 0

        total_seconds = (
            self.config.duration_minutes
            * 60
        )

        remaining = (
            total_seconds
            - self.elapsed_seconds()
        )

        return max(
            0,
            remaining
        )

    # ========================================
    # Remaining Minutes
    # ========================================

    def remaining_minutes(self):

        return round(
            self.remaining_seconds()
            / 60,
            1
        )

    # ========================================
    # Find phase index
    # ========================================

    def _get_phase_index(
        self,
        phase_name
    ):

        for index, phase in enumerate(
            self.plan.phases
        ):

            if phase.name == phase_name:

                return index

        return -1

    # ========================================
    # Automatic phase
    # ========================================

    def _calculate_phase_index(self):

        elapsed_minutes = (
            self.elapsed_seconds()
            / 60
        )

        accumulated = 0

        for index, phase in enumerate(
            self.plan.phases
        ):

            accumulated += phase.minutes

            if elapsed_minutes < accumulated:

                return index

        return (
            len(self.plan.phases) - 1
        )

    # ========================================
    # Update phase
    # ========================================

    def update_phase(self):

        if self.started_at is None:

            self.phase = "not_started"

            self.phase_index = -1

            return self.phase

        if self.ended:

            self.phase = "completed"

            return self.phase

        if self.remaining_seconds() <= 0:

            self.end()

            return self.phase

        # 当前阶段被主动锁定
        if self.phase_override is not None:

            self.phase = (
                self.phase_override
            )

            self.phase_index = (
                self._get_phase_index(
                    self.phase_override
                )
            )

            return self.phase

        # 否则按时间自动计算
        self.phase_index = (
            self._calculate_phase_index()
        )

        self.phase = (
            self.plan
            .phases[
                self.phase_index
            ]
            .name
        )

        return self.phase

    # ========================================
    # Current phase
    # ========================================

    def get_current_phase(self):

        self.update_phase()

        if (
            self.phase == "completed"
            or self.phase == "not_started"
        ):

            return None

        if (
            self.phase_index < 0
            or self.phase_index >= len(
                self.plan.phases
            )
        ):

            return None

        return (
            self.plan
            .phases[
                self.phase_index
            ]
        )

    # ========================================
    # Status
    # ========================================

    def get_status(self):

        self.update_phase()

        current_phase = (
            self.get_current_phase()
        )

        phase_minutes = (
            current_phase.minutes
            if current_phase
            else 0
        )

        return {
            "phase": self.phase,

            "phase_index":
                self.phase_index,

            "phase_minutes":
                phase_minutes,

            "elapsed_seconds":
                self.elapsed_seconds(),

            "remaining_seconds":
                self.remaining_seconds(),

            "remaining_minutes":
                self.remaining_minutes(),

            "duration_minutes":
                self.config.duration_minutes,

            "phase_override":
                self.phase_override
        }

    # ========================================
    # Force phase
    # ========================================

    def set_phase(
        self,
        phase
    ):

        valid_phases = [
            item.name
            for item in self.plan.phases
        ]

        valid_phases.append(
            "completed"
        )

        if phase not in valid_phases:

            raise ValueError(
                f"Invalid phase: {phase}"
            )

        self.phase = phase

        self.phase_index = (
            self._get_phase_index(
                phase
            )
        )

        self.phase_override = phase

        if phase == "completed":

            self.ended = True

    # ========================================
    # Clear override
    # ========================================

    def clear_phase_override(self):

        self.phase_override = None

        if not self.ended:

            self.update_phase()

    # ========================================
    # Next phase
    # ========================================

    def next_phase(self):

        if self.ended:

            return "completed"

        # 如果当前还没有阶段
        if self.phase_index < 0:

            self.phase_index = 0

            self.phase = (
                self.plan
                .phases[0]
                .name
            )

            self.phase_override = (
                self.phase
            )

            return self.phase

        next_index = (
            self.phase_index + 1
        )

        # 已经是最后一个阶段
        if next_index >= len(
            self.plan.phases
        ):

            self.end()

            return "completed"

        self.phase_index = next_index

        self.phase = (
            self.plan
            .phases[
                self.phase_index
            ]
            .name
        )

        # 关键：
        # 主动进入下一阶段时暂时锁定阶段，
        # 防止 get_status() 又按时间退回旧阶段。
        self.phase_override = (
            self.phase
        )

        return self.phase

    # ========================================
    # End
    # ========================================

    def end(self):

        self.ended = True

        self.phase = "completed"

        self.phase_index = len(
            self.plan.phases
        )

        self.phase_override = "completed"

    # ========================================
    # Can continue
    # ========================================

    def can_continue(self):

        return (
            not self.ended
            and self.remaining_seconds() > 0
        )

    # ========================================
    # Print plan
    # ========================================

    def print_plan(self):

        self.plan.print_plan()