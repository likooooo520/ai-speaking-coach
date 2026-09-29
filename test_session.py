from app.session import (
    SessionConfig,
    SessionManager
)


def print_status(session):

    status = (
        session.get_status()
    )

    print(
        f"Phase: "
        f"{status['phase']}"
    )

    print(
        f"Phase index: "
        f"{status['phase_index']}"
    )

    print(
        f"Phase duration: "
        f"{status['phase_minutes']} min"
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
        "   Session + Plan Integration"
    )

    print(
        "================================"
    )

    print()

    # ========================================
    # 45-minute session
    # ========================================

    config = SessionConfig(
        duration_minutes=45
    )

    session = SessionManager(
        config
    )

    print(
        "Session plan:"
    )

    session.print_plan()

    # ========================================
    # Start
    # ========================================

    print()
    print(
        "Starting session..."
    )

    session.start()

    print_status(
        session
    )

    # ========================================
    # Test next phase
    # ========================================

    print(
        "Move to next phase:"
    )

    session.next_phase()

    print_status(
        session
    )

    session.next_phase()

    print_status(
        session
    )

    # ========================================
    # Test override
    # ========================================

    print(
        "Force targeted practice:"
    )

    session.set_phase(
        "targeted_practice"
    )

    print_status(
        session
    )

    # ========================================
    # Clear override
    # ========================================

    print(
        "Clear override:"
    )

    session.clear_phase_override()

    print_status(
        session
    )

    # ========================================
    # Test end
    # ========================================

    print(
        "Ending session..."
    )

    session.end()

    print_status(
        session
    )

    print(
        "Can continue:",
        session.can_continue()
    )

    print()
    print(
        "Test completed."
    )


if __name__ == "__main__":

    main()