from app.adaptive_session import (
    AdaptiveSession
)


def show_status(
    adaptive
):

    status = adaptive.status()

    print(
        f"Phase: {status['phase']}"
    )

    print(
        f"Phase index: "
        f"{status['phase_index']}"
    )

    print(
        f"Remaining: "
        f"{status['remaining_minutes']} min"
    )

    print()


def main():

    print()
    print(
        "================================"
    )

    print(
        "   Adaptive Session Test"
    )

    print(
        "================================"
    )

    adaptive = AdaptiveSession(
        duration_minutes=45
    )

    adaptive.start()

    print(
        "Initial:"
    )

    show_status(
        adaptive
    )

    # ========================================
    # Normal
    # ========================================

    print(
        "Test 1: normal performance"
    )

    decision = adaptive.route(
        performance_band="normal"
    )

    print(
        f"Action: {decision.action}"
    )

    print(
        f"Target: {decision.target_phase}"
    )

    show_status(
        adaptive
    )

    # ========================================
    # Strong
    # ========================================

    print(
        "Test 2: strong performance"
    )

    # 先进入主对话
    adaptive.session.set_phase(
        "main_conversation"
    )

    decision = adaptive.route(
        performance_band="strong"
    )

    print(
        f"Action: {decision.action}"
    )

    print(
        f"Target: {decision.target_phase}"
    )

    show_status(
        adaptive
    )

    # ========================================
    # Repeated Error
    # ========================================

    print(
        "Test 3: repeated error"
    )

    adaptive.session.set_phase(
        "main_conversation"
    )

    decision = adaptive.route(
        performance_band="normal",
        repeated_error_count=3
    )

    print(
        f"Action: {decision.action}"
    )

    print(
        f"Target: {decision.target_phase}"
    )

    show_status(
        adaptive
    )

    # ========================================
    # Weak Challenge
    # ========================================

    print(
        "Test 4: weak challenge"
    )

    adaptive.session.set_phase(
        "challenge"
    )

    decision = adaptive.route(
        performance_band="weak"
    )

    print(
        f"Action: {decision.action}"
    )

    print(
        f"Target: {decision.target_phase}"
    )

    show_status(
        adaptive
    )

    # ========================================
    # End
    # ========================================

    adaptive.end()

    print(
        "After end:"
    )

    show_status(
        adaptive
    )

    print(
        "Can continue:",
        adaptive.can_continue()
    )

    print()
    print(
        "Test completed."
    )


if __name__ == "__main__":

    main()