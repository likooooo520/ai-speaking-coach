from app.llm import DeepSeekCoach


def main():

    print()
    print("================================")
    print("    DeepSeek Connection Test")
    print("================================")
    print()

    coach = DeepSeekCoach()

    coach.set_session_context(
        duration_minutes=45,
        phase="warmup",
        topic="food",
        language_mode="auto",
        coach_mode="automatic"
    )

    decision = coach.chat(
        "I really like Chinese food. "
        "My favorite dish is hot pot."
    )

    print()
    print("================================")
    print("Response")
    print("================================")
    print()

    print(
        decision.reply
    )

    print()
    print(
        "Overall:",
        decision.performance.overall
    )

    print(
        "Band:",
        decision.performance.band
    )

    print()
    print(
        "Test completed."
    )


if __name__ == "__main__":

    main()