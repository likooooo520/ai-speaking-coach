from app.performance import PerformanceTracker


TEST_FILE = "data/test_performance.json"


def create_tracker():
    tracker = PerformanceTracker(
        file_path=TEST_FILE
    )

    # 重置测试数据
    tracker.data = {
        "current_difficulty": "B2",
        "recent_performance": [],
        "strong_streak": 0,
        "weak_streak": 0,
        "sessions": 0
    }

    tracker.save()

    return tracker


def print_result(
    round_number,
    tracker,
    action
):

    print(
        f"Round {round_number}: "
        f"action={action}, "
        f"difficulty="
        f"{tracker.get_current_difficulty()}, "
        f"strong_streak="
        f"{tracker.data['strong_streak']}, "
        f"weak_streak="
        f"{tracker.data['weak_streak']}"
    )


def main():

    print()
    print("================================")
    print("   Difficulty Engine Test")
    print("================================")
    print()

    tracker = create_tracker()

    # ========================================
    # Test A
    # strong × 3
    # ========================================

    print("Test A: strong × 3")
    print()

    for i in range(1, 4):

        tracker.record(
            {
                "fluency": 9.0,
                "grammar": 9.0,
                "vocabulary": 8.5,
                "naturalness": 8.5,
                "overall": 8.8,
                "band": "strong"
            },
            "increase"
        )

        difficulty, action = (
            tracker.adjust_difficulty()
        )

        print_result(
            i,
            tracker,
            action
        )

    print()

    print(
        "Expected: B2 → B2+"
    )

    print()

    # ========================================
    # Test B
    # weak × 2
    # ========================================

    print("Test B: weak × 2")
    print()

    for i in range(1, 3):

        tracker.record(
            {
                "fluency": 4.5,
                "grammar": 5.0,
                "vocabulary": 5.0,
                "naturalness": 4.5,
                "overall": 4.8,
                "band": "weak"
            },
            "decrease"
        )

        difficulty, action = (
            tracker.adjust_difficulty()
        )

        print_result(
            i,
            tracker,
            action
        )

    print()

    print(
        "Expected: B2+ → B2"
    )

    print()
    print("================================")
    print("Test completed.")
    print("================================")


if __name__ == "__main__":
    main()