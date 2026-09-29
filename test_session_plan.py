from app.session_plan import SessionPlan


def test_duration(duration):

    print()
    print(
        "================================"
    )

    print(
        f"Testing: {duration} minutes"
    )

    print(
        "================================"
    )

    plan = SessionPlan(
        duration
    )

    plan.print_plan()

    total = plan.total_minutes()

    print()
    print(
        f"Expected total: {duration}"
    )

    print(
        f"Actual total:   {total}"
    )

    if total != duration:

        raise AssertionError(
            f"Duration mismatch: "
            f"expected {duration}, "
            f"got {total}"
        )

    print(
        "✅ Duration check passed"
    )


def main():

    durations = [
        15,
        20,
        30,
        45,
        60,
        75
    ]

    for duration in durations:

        test_duration(
            duration
        )

    print()
    print(
        "================================"
    )

    print(
        "All Session Plan tests passed!"
    )

    print(
        "================================"
    )


if __name__ == "__main__":

    main()