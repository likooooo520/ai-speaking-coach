import json
import re
from pathlib import Path


class NaturalnessMemory:

    @staticmethod
    def normalize_original(original):
        return re.sub(r"\s+", " ", (original or "").strip().lower())

    def __init__(
        self,
        file_path="data/naturalness_memory.json"
    ):

        self.file_path = Path(file_path)

        self.file_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.data = {
            "expressions": []
        }

        self.load()

    # ========================================
    # Load
    # ========================================

    def load(self):

        if not self.file_path.exists():

            self.data = {
                "expressions": []
            }

            self.save()

            return

        try:

            with open(
                self.file_path,
                "r",
                encoding="utf-8"
            ) as f:

                self.data = json.load(f)

        except Exception as e:

            print()
            print("⚠️ Naturalness Memory 读取失败")
            print(f"错误：{e}")
            print()

            self.data = {
                "expressions": []
            }

    # ========================================
    # Save
    # ========================================

    def save(self):

        try:

            with open(
                self.file_path,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    self.data,
                    f,
                    ensure_ascii=False,
                    indent=4
                )

        except Exception as e:

            print()
            print("⚠️ Naturalness Memory 保存失败")
            print(f"错误：{e}")
            print()

    # ========================================
    # Add Expression
    # ========================================

    def add_expression(
        self,
        original,
        alternatives,
        category="expression",
        frequency_increment=1
    ):

        original = original.strip()

        if not original:
            return None

        # 确保 alternatives 是列表
        if isinstance(
            alternatives,
            str
        ):
            alternatives = [
                alternatives
            ]

        alternatives = [
            item.strip()
            for item in alternatives
            if item and item.strip()
        ]

        if not alternatives:
            return None

        # 查找已存在的表达
        for expression in self.data[
            "expressions"
        ]:

            if self.normalize_original(expression["original"]) == self.normalize_original(original):

                expression["frequency"] += (
                    frequency_increment
                )

                expression["alternatives"] = (
                    alternatives
                )

                expression["category"] = (
                    category
                )

                self.save()

                return expression

        # 新表达
        new_expression = {
            "original": original,
            "alternatives": alternatives,
            "category": category,
            "frequency": frequency_increment,
            "status": "learning"
        }

        self.data[
            "expressions"
        ].append(
            new_expression
        )

        self.save()

        return new_expression

    # ========================================
    # Get All
    # ========================================

    def get_all_expressions(self):

        return self.data.get(
            "expressions",
            []
        )

    # ========================================
    # Get Important Expressions
    # ========================================

    def get_important_expressions(
        self,
        limit=5
    ):

        expressions = (
            self.get_all_expressions()
        )

        sorted_expressions = sorted(
            expressions,
            key=lambda item: item.get(
                "frequency",
                0
            ),
            reverse=True
        )

        return sorted_expressions[:limit]

    def find_expression(self, original):
        normalized = self.normalize_original(original)
        for expression in self.get_all_expressions():
            if self.normalize_original(expression["original"]) == normalized:
                return expression
        return None

    def get_expression_frequency(self, original):
        expression = self.find_expression(original)
        return expression.get("frequency", 0) if expression else 0

    def match_current_expression(self, original):
        return self.find_expression(original)

    # ========================================
    # Generate LLM Context
    # ========================================

    def get_llm_context(
        self,
        limit=5
    ):

        expressions = (
            self.get_important_expressions(
                limit=limit
            )
        )

        if not expressions:

            return (
                "No previous naturalness patterns "
                "have been recorded."
            )

        lines = []

        lines.append(
            "KNOWN NATURALNESS PATTERNS:"
        )

        lines.append("")

        for index, item in enumerate(
            expressions,
            start=1
        ):

            alternatives = ", ".join(
                item["alternatives"]
            )

            lines.append(
                f"{index}. "
                f"{item['original']}"
            )

            lines.append(
                f"   more natural: "
                f"{alternatives}"
            )

            lines.append(
                f"   category: "
                f"{item['category']}"
            )

            lines.append(
                f"   frequency: "
                f"{item['frequency']}"
            )

            lines.append(
                f"   status: "
                f"{item['status']}"
            )

            lines.append("")

        lines.append(
            "Use these patterns only when they "
            "are relevant to the current conversation."
        )

        return "\n".join(lines)

    # ========================================
    # Mark as Practiced
    # ========================================

    def mark_practiced(
        self,
        original
    ):

        original = original.strip().lower()

        for expression in self.data[
            "expressions"
        ]:

            if (
                expression["original"].lower()
                == original
            ):

                if (
                    expression["frequency"]
                    >= 5
                ):
                    expression["status"] = (
                        "improving"
                    )

                if (
                    expression["frequency"]
                    >= 10
                ):
                    expression["status"] = (
                        "mastered"
                    )

                self.save()

                return expression

        return None

    # ========================================
    # Print Memory
    # ========================================

    def print_memory(self):

        expressions = (
            self.get_all_expressions()
        )

        print()
        print(
            "══════════════════════════════════"
        )

        print(
            "       Naturalness Memory"
        )

        print(
            "══════════════════════════════════"
        )

        if not expressions:

            print()
            print(
                "No naturalness patterns recorded."
            )

        else:

            for index, item in enumerate(
                expressions,
                start=1
            ):

                print()
                print(
                    f"{index}. "
                    f"{item['original']}"
                )

                print(
                    f"   → "
                    f"{', '.join(item['alternatives'])}"
                )

                print(
                    f"   Category: "
                    f"{item['category']}"
                )

                print(
                    f"   Frequency: "
                    f"{item['frequency']}"
                )

                print(
                    f"   Status: "
                    f"{item['status']}"
                )

        print()
        print(
            "══════════════════════════════════"
        )
