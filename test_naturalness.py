from app.naturalness import NaturalnessMemory


print()
print("================================")
print("    Naturalness Memory Test")
print("================================")


memory = NaturalnessMemory()


print()
print("测试 1：添加 natural expression")
print()

memory.add_expression(
    original="I think",
    alternatives=[
        "I'd say",
        "Personally",
        "I feel like"
    ],
    category="spoken_expression"
)


print("测试 2：重复一次")
print()

memory.add_expression(
    original="I think",
    alternatives=[
        "I'd say",
        "Personally",
        "I feel like"
    ],
    category="spoken_expression"
)


print()
print("当前 Memory：")

memory.print_memory()


print()
print("LLM Context:")
print()

print(
    memory.get_llm_context(
        limit=5
    )
)


print()
print("测试完成。")