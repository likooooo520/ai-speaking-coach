from pathlib import Path
from uuid import uuid4

from app.stt import SpeechToText
from app.llm import DeepSeekCoach
from app.adaptive_session import AdaptiveSession
from app.application.turn_processor import TurnProcessor
from app.application.learning_update_service import LearningUpdateService
from app.application.agent_orchestrator import AgentOrchestrator
from app.domain.turn import TurnContext


AUDIO_FILE = Path(
    "data/audio/user_speech.wav"
)


def choose_duration():

    print()
    print(
        "How long would you like to practice?"
    )

    print(
        "1. 15 minutes"
    )

    print(
        "2. 30 minutes"
    )

    print(
        "3. 45 minutes"
    )

    print(
        "4. 60 minutes"
    )

    print(
        "5. Custom"
    )

    while True:

        choice = input(
            "\nChoose 1-5: "
        ).strip()

        if choice == "1":

            return 15

        if choice == "2":

            return 30

        if choice == "3":

            return 45

        if choice == "4":

            return 60

        if choice == "5":

            while True:

                value = input(
                    "Enter minutes (5-180): "
                ).strip()

                try:

                    minutes = int(
                        value
                    )

                except ValueError:

                    print(
                        "Please enter a number."
                    )

                    continue

                if 5 <= minutes <= 180:

                    return minutes

                print(
                    "Please enter a value "
                    "between 5 and 180."
                )

        print(
            "Please choose 1, 2, 3, 4, or 5."
        )


def choose_topic():

    print()

    print(
        "What would you like to talk about?"
    )

    print(
        "Examples: food, travel, work, "
        "movies, technology, daily life"
    )

    topic = input(
        "Topic: "
    ).strip()

    if not topic:

        topic = "general conversation"

    return topic


def print_session_header(
    duration,
    topic,
    status
):

    print()
    print(
        "================================"
    )

    print(
        "       AI Speaking Coach"
    )

    print(
        "           V0.3.7"
    )

    print(
        "================================"
    )

    print()

    print(
        f"Duration: {duration} min"
    )

    print(
        f"Topic: {topic}"
    )

    print(
        "Level: B2"
    )

    print(
        "Mode: Automatic Adjustment"
    )

    print(
        f"Phase: {status['phase']}"
    )

    print()


def print_decision(
    decision,
    status,
    router_decision,
    action_result=None
):

    print()
    print(
        "🤖 Coach:"
    )

    print(
        decision.reply
    )

    print()
    print(
        "──────── Coach Analysis ────────"
    )

    print(
        f"Phase: {status['phase']}"
    )

    print(
        f"Difficulty: "
        f"{decision.difficulty}"
    )

    print(
        f"Topic: "
        f"{decision.conversation_topic}"
    )

    # ========================================
    # Performance
    # ========================================

    performance = (
        decision.performance
    )

    print()
    print(
        "📊 Performance:"
    )

    print(
        f"Fluency: "
        f"{performance.fluency:.1f}/10"
    )

    print(
        f"Grammar: "
        f"{performance.grammar:.1f}/10"
    )

    print(
        f"Vocabulary: "
        f"{performance.vocabulary:.1f}/10"
    )

    print(
        f"Naturalness: "
        f"{performance.naturalness:.1f}/10"
    )

    print(
        f"Overall: "
        f"{performance.overall:.1f}/10"
    )

    print(
        f"Band: "
        f"{performance.band}"
    )

    # ========================================
    # Correction
    # ========================================

    if decision.correction.needed:

        print()
        print(
            "📝 Correction:"
        )

        print(
            f"Original: "
            f"{decision.correction.original}"
        )

        print(
            f"Better: "
            f"{decision.correction.better}"
        )

        if decision.correction.explanation:

            print(
                f"Explanation: "
                f"{decision.correction.explanation}"
            )

    # ========================================
    # Naturalness
    # ========================================

    if decision.naturalness.detected:

        print()
        print(
            "✨ Naturalness:"
        )

        print(
            f"Original: "
            f"{decision.naturalness.original}"
        )

        alternatives = ", ".join(
            decision
            .naturalness
            .alternatives
        )

        print(
            f"More natural: "
            f"{alternatives}"
        )

        if decision.naturalness.explanation:

            print(
                "Explanation: "
                + decision
                .naturalness
                .explanation
            )

    # ========================================
    # ASR
    # ========================================

    if decision.asr_uncertainty:

        print()
        print(
            "🎧 Possible ASR issue:"
        )

        for item in (
            decision.asr_uncertainty
        ):

            print(
                f"'{item.heard}'"
                f" → "
                f"'{item.possible}'"
                f" "
                f"(confidence: "
                f"{item.confidence})"
            )

    # ========================================
    # Router
    # ========================================

    print()
    print(
        "🧭 Session Router:"
    )

    print(
        f"Action: "
        f"{router_decision.action}"
    )

    print(
        f"Reason: "
        f"{router_decision.reason}"
    )

    if router_decision.target_phase:

        print(
            f"Next phase: "
            f"{router_decision.target_phase}"
        )

    print(
        "──────────────────────────────"
    )

    if action_result is not None:

        print(
            f"Agent action: {action_result.action.value}"
        )

        if not action_result.executed:

            print(
                f"Agent action unavailable: {action_result.reason}"
            )


def main():

    # ========================================
    # Session setup
    # ========================================

    duration = choose_duration()

    topic = choose_topic()

    # ========================================
    # Initialize components
    # ========================================

    adaptive = AdaptiveSession(
        duration_minutes=duration
    )

    session_id = str(uuid4())

    coach = DeepSeekCoach()
    turn_processor = TurnProcessor(coach)
    learning_update_service = LearningUpdateService(
        coach.error_memory,
        coach.naturalness_memory,
        coach.performance_tracker,
    )
    agent_orchestrator = AgentOrchestrator()

    stt = SpeechToText()

    adaptive.start()

    status = adaptive.status()

    print_session_header(
        duration,
        topic,
        status
    )

    print(
        "Session started."
    )

    print(
        "Press Enter to begin speaking."
    )

    # ========================================
    # Main Session Loop
    # ========================================

    while adaptive.can_continue():

        # ------------------------------------
        # Prepare current turn
        # ------------------------------------

        status = (
            adaptive.prepare_turn()
        )

        if not adaptive.can_continue():

            break

        # ------------------------------------
        # Prepare Targeted Practice Context
        # ------------------------------------

        targeted_context = ""

        if (
            status["phase"]
            == "targeted_practice"
        ):

            targeted_context = (
                adaptive
                .targeted_context()
            )

        print()
        print(
            "════════════════════════════════"
        )

        print(
            f"Phase: "
            f"{status['phase']}"
        )

        print(
            f"Turn: "
            f"{status['turn_count'] + 1}"
        )

        print(
            f"Phase remaining: "
            f"{status['phase_remaining_minutes']} min"
        )

        print(
            f"Session remaining: "
            f"{status['remaining_minutes']} min"
        )

        # Targeted Practice step
        if (
            status["phase"]
            == "targeted_practice"
        ):

            print(
                f"Practice step: "
                f"{status['targeted_practice_step']}"
            )

        print(
            "════════════════════════════════"
        )

        # ------------------------------------
        # User command
        # ------------------------------------

        command = input(
            "\nPress Enter to speak, "
            "or type q to end: "
        ).strip()

        if command.lower() == "q":

            break

        # ------------------------------------
        # Record voice
        # ------------------------------------

        stt.record(
            str(AUDIO_FILE),
            duration=10
        )

        # ------------------------------------
        # Whisper
        # ------------------------------------

        user_text = (
            stt.transcribe(
                str(AUDIO_FILE)
            )
        )

        print()
        print(
            "👤 You:"
        )

        print(
            user_text
        )

        if not user_text:

            print(
                "No speech detected."
            )

            continue

        # ------------------------------------
        # DeepSeek Coach
        # ------------------------------------

        turn_context = TurnContext(
            session_id=session_id,
            turn_id=status["turn_count"] + 1,
            phase=status["phase"],
            user_text=user_text,
            targeted_practice_context=targeted_context,
            duration_minutes=duration,
            topic=topic,
            language_mode="auto",
        )

        turn_result = turn_processor.process(
            turn_context
        )

        decision = turn_result.decision

        # ------------------------------------
        # Agent Decision Loop
        # ------------------------------------

        action_result = agent_orchestrator.run(
            turn_result,
            mode="foreign_friend",
            session_context={
                "in_targeted_practice": status["phase"] == "targeted_practice",
            },
            error_memory=coach.error_memory,
            naturalness_memory=coach.naturalness_memory,
        )

        # ------------------------------------
        # System Error
        # ------------------------------------

        if decision.system_error:

            print()
            print(
                "⚠️ This turn was not evaluated "
                "because the coach service was "
                "unavailable."
            )

            print(
                "Your performance and difficulty "
                "will remain unchanged."
            )

            print(
                "Please try speaking again."
            )

            continue

        # ------------------------------------
        # Valid Turn
        # ------------------------------------

        learning_update_service.apply(turn_result)

        adaptive.record_turn()

        # ------------------------------------
        # Current Error
        # ------------------------------------

        current_error_detected = (
            decision.correction.needed
            and bool(decision.correction.original)
            and bool(decision.correction.better)
        )

        # ------------------------------------
        # Historical repeated errors
        # ------------------------------------

        current_error = (
            decision.correction.original
            if current_error_detected
            else None
        )

        matched_historical_error = (
            coach.error_memory.match_current_error(
                current_error
            )
            if current_error
            else None
        )

        current_error_frequency = (
            coach.error_memory.get_error_frequency(
                current_error
            )
            if current_error
            else 0
        )

        # ------------------------------------
        # Naturalness
        # ------------------------------------

        current_naturalness_detected = (
            decision
            .naturalness
            .detected
        )

        naturalness_items = (
            coach
            .naturalness_memory
            .get_important_expressions(
                limit=5
            )
        )

        naturalness_count = len(
            naturalness_items
        )

        current_naturalness = (
            decision.naturalness.original
            if current_naturalness_detected
            else None
        )

        matched_historical_naturalness = (
            coach.naturalness_memory.match_current_expression(
                current_naturalness
            )
            if current_naturalness
            else None
        )

        current_naturalness_frequency = (
            coach.naturalness_memory.get_expression_frequency(
                current_naturalness
            )
            if current_naturalness
            else 0
        )

        # ------------------------------------
        # Session Router
        # ------------------------------------

        router_decision = adaptive.route(
            performance_band=(
                decision
                .performance
                .band
            ),
            naturalness_count=(
                naturalness_count
            ),
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

        # ------------------------------------
        # Start Targeted Practice
        # ------------------------------------

        if (
            router_decision.target_phase
            == "targeted_practice"
        ):

            started = (
                adaptive
                .start_targeted_practice(
                    decision,
                    focus_type=(
                        "error"
                        if current_error_detected
                        else "naturalness"
                    )
                )
            )

            if started:

                print()
                print(
                    "🎯 Targeted Practice Started"
                )

                print(
                    adaptive
                    .targeted_practice
                    .focus_text()
                )

        # ------------------------------------
        # Targeted Practice progress
        # ------------------------------------

        if (
            status["phase"]
            == "targeted_practice"
        ):

            completed = (
                adaptive
                .advance_targeted_practice()
            )

            if completed:

                print()
                print(
                    "✅ Targeted Practice completed."
                )

                adaptive.next_phase()

        # ------------------------------------
        # Get updated status
        # ------------------------------------

        status = adaptive.status()

        # ------------------------------------
        # Display
        # ------------------------------------

        print_decision(
            decision,
            status,
            router_decision,
            action_result,
        )

        # ------------------------------------
        # Session complete
        # ------------------------------------

        if not adaptive.can_continue():

            break

    # ========================================
    # End Session
    # ========================================

    adaptive.end()

    print()
    print(
        "================================"
    )

    print(
        "       Session Ended"
    )

    print(
        "================================"
    )

    print()

    print(
        f"Duration: {duration} min"
    )

    print(
        f"Topic: {topic}"
    )

    print()

    print(
        "Your learning data has been saved."
    )


if __name__ == "__main__":

    main()
