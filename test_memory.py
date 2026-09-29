from app.memory import ErrorMemory


print()
print("================================")
print("       Error Memory Test")
print("================================")


memory = ErrorMemory()


print()
print("当前 Memory：")

memory.print_memory()


print()
print("================================")
print("测试 LLM Memory Context")
print("================================")


context = memory.get_llm_context(
    limit=5
)


print()
print(context)
print()


print("================================")
print("测试完成")
print("================================")