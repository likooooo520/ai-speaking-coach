from app.targeted_practice import (
    TargetedPracticeManager
)


def main():

    print()
    print(
        "================================"
    )

    print(
        "   Targeted Practice Test"
    )

    print(
        "================================"
    )

    practice = (
        TargetedPracticeManager()
    )

    practice.start(
        original="many food",
        better="many kinds of food",
        explanation=(
            "Food is uncountable in this context."
        ),
        category="vocabulary"
    )

    print()
    print(
        "Initial Context:"
    )

    print(
        practice.get_context()
    )

    for _ in range(4):

        print()
        print(
            f"Step: "
            f"{practice.current_step()}"
        )

        print(
            f"Name: "
            f"{practice.step_name()}"
        )

        print()

        practice.advance()

    print()

    print(
        "Completed:",
        practice.is_completed()
    )

    print()
    print(
        "Test completed."
    )


if __name__ == "__main__":

    main()