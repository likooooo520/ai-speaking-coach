from dataclasses import dataclass


@dataclass
class PracticeFocus:

    type: str

    original: str

    better: str = ""

    alternatives: list[str] | None = None

    explanation: str = ""

    category: str = "general"


class TargetedPracticeManager:

    def __init__(self):

        self.focus = None

        self.step = 0

        self.active = False

        self.completed = False

    # ========================================
    # Start Practice
    # ========================================

    def start(
        self,
        original,
        better="",
        explanation="",
        category="general",
        focus_type="error",
        alternatives=None
    ):

        self.focus = PracticeFocus(
            type=focus_type,
            original=original,
            better=better,
            alternatives=alternatives or [],
            explanation=explanation,
            category=category
        )

        self.step = 1

        self.active = True

        self.completed = False

    # ========================================
    # Has Focus
    # ========================================

    def has_focus(self):

        return (
            self.focus is not None
            and self.active
        )

    # ========================================
    # Current Step
    # ========================================

    def current_step(self):

        return self.step

    # ========================================
    # Step Name
    # ========================================

    def step_name(self):

        names = {
            1: "correction",
            2: "repetition",
            3: "variation",
            4: "free_use"
        }

        return names.get(
            self.step,
            "completed"
        )

    # ========================================
    # LLM Context
    # ========================================

    def get_context(self):

        if not self.has_focus():

            return (
                "No targeted practice is currently active."
            )

        focus = self.focus

        if self.step == 1:

            if focus.type == "naturalness":
                instruction = (
                    "Briefly explain the more natural expression "
                    "and ask the learner to use it."
                )
            else:
                instruction = (
                    "First, briefly explain the learner's "
                    "specific mistake and ask them to repeat "
                    "the corrected sentence."
                )

        elif self.step == 2:

            instruction = (
                "Ask the learner to use the corrected "
                "expression again in a closely related "
                "sentence."
            )

        elif self.step == 3:

            instruction = (
                "Give the learner a slightly different "
                "situation and ask them to use the same "
                "language pattern."
            )

        elif self.step == 4:

            instruction = (
                "Let the learner use the corrected pattern "
                "freely in conversation. Do not turn this "
                "into a grammar lecture."
            )

        else:

            instruction = (
                "Finish the targeted practice naturally."
            )

        return (
            "TARGETED PRACTICE FOCUS:\n"
            f"Original: {focus.original}\n"
            f"Type: {focus.type}\n"
            f"Better: {focus.better}\n"
            f"Alternatives: {', '.join(focus.alternatives or [])}\n"
            f"Category: {focus.category}\n"
            f"Explanation: {focus.explanation}\n"
            f"Current step: {self.step} "
            f"({self.step_name()})\n\n"
            f"Instruction: {instruction}"
        )

    # ========================================
    # Advance
    # ========================================

    def advance(self):

        if not self.active:

            return

        self.step += 1

        if self.step > 4:

            self.active = False

            self.completed = True

    # ========================================
    # Complete
    # ========================================

    def complete(self):

        self.active = False

        self.completed = True

        self.step = 5

    # ========================================
    # Is Completed
    # ========================================

    def is_completed(self):

        return self.completed

    # ========================================
    # Focus Text
    # ========================================

    def focus_text(self):

        if self.focus is None:

            return None

        return (
            f"[{self.focus.type}] "
            f"{self.focus.original} "
            f"→ {self.focus.better or ', '.join(self.focus.alternatives or [])}"
        )
