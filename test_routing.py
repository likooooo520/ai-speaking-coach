from app.routing import SessionRouter


def test(
    current_phase,
    performance_band,
    repeated_error_count,
    remaining_minutes
):

    router = SessionRouter()

    decision = router.decide(
        current_phase=current_phase,
        performance_band=performance_band,
        repeated_error_count=repeated_error_count,
        remaining_minutes=remaining_minutes
    )

    print()
    print(
        f"Phase: {current_phase}"
    )

    print(
        f"Performance: {performance_band}"
    )

    print(
        f"Repeated errors: "
        f"{repeated_error_count}"
    )

    print(
        f"Remaining: "
        f"{remaining_minutes} min"
    )

    print(
        f"Action: "
        f"{decision.action}"
    )

    print(
        f"Reason: "
        f"{decision.reason}"
    )

    print(
        f"Target: "
        f"{decision.target_phase}"
    )


def main():

    print()
    print(
        "================================"
    )

    print(
        "       Session Router Test"
    )

    print(
        "================================"
    )

    # ========================================
    # Test 1
    # ========================================

    print()
    print("Test 1: Strong performance")

    test(
        current_phase="main_conversation",
        performance_band="strong",
        repeated_error_count=0,
        remaining_minutes=20
    )

    # ========================================
    # Test 2
    # ========================================

    print()
    print("Test 2: Repeated error")

    test(
        current_phase="main_conversation",
        performance_band="normal",
        repeated_error_count=3,
        remaining_minutes=15
    )

    # ========================================
    # Test 3
    # ========================================

    print()
    print("Test 3: Weak challenge")

    test(
        current_phase="challenge",
        performance_band="weak",
        repeated_error_count=0,
        remaining_minutes=15
    )

    # ========================================
    # Test 4
    # ========================================

    print()
    print("Test 4: Near session end")

    test(
        current_phase="main_conversation",
        performance_band="normal",
        repeated_error_count=0,
        remaining_minutes=4
    )

    # ========================================
    # Test 5
    # ========================================

    print()
    print("Test 5: Normal conversation")

    test(
        current_phase="main_conversation",
        performance_band="normal",
        repeated_error_count=0,
        remaining_minutes=20
    )

    print()
    print(
        "================================"
    )

    print(
        "Test completed."
    )

    print(
        "================================"
    )


if __name__ == "__main__":

    main()