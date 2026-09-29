import json
import re
from pathlib import Path


class ErrorMemory:

    @staticmethod
    def normalize_original(original):
        return re.sub(r"\s+", " ", (original or "").strip().lower())

    def __init__(
        self,
        file_path="data/error_memory.json"
    ):

        self.file_path = Path(file_path)

        self.file_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.data = {
            "errors": []
        }

        self.load()

    # ========================================
    # Load
    # ========================================

    def load(self):

        if not self.file_path.exists():

            self.data = {
                "errors": []
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
            print("⚠️ Error Memory 读取失败")
            print(f"错误：{e}")
            print()

            self.data = {
                "errors": []
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
            print("⚠️ Error Memory 保存失败")
            print(f"错误：{e}")
            print()

    # ========================================
    # Add Error
    # ========================================

    def add_error(
        self,
        original,
        better,
        category="general",
        severity="medium"
    ):

        original = original.strip()
        better = better.strip()

        if not original or not better:
            return None

        # 查找相同错误
        for error in self.data["errors"]:

            if self.normalize_original(error["original"]) == self.normalize_original(original):

                error["count"] += 1

                error["better"] = better

                error["category"] = category

                error["severity"] = severity

                self.save()

                return error

        # 创建新错误
        new_error = {
            "original": original,
            "better": better,
            "category": category,
            "severity": severity,
            "count": 1
        }

        self.data["errors"].append(
            new_error
        )

        self.save()

        return new_error

    # ========================================
    # Get All Errors
    # ========================================

    def get_all_errors(self):

        return self.data.get(
            "errors",
            []
        )

    # ========================================
    # Get Important Errors
    # ========================================

    def get_important_errors(
        self,
        limit=5
    ):

        errors = self.get_all_errors()

        # count 越高越重要
        sorted_errors = sorted(
            errors,
            key=lambda error: error.get(
                "count",
                0
            ),
            reverse=True
        )

        return sorted_errors[:limit]

    # ========================================
    # Get Repeated Errors
    # ========================================

    def get_repeated_errors(
        self,
        minimum_count=2
    ):

        return [
            error
            for error in self.get_all_errors()
            if error.get("count", 0)
            >= minimum_count
        ]

    # ========================================
    # Find Error
    # ========================================

    def find_error(
        self,
        original
    ):

        original = self.normalize_original(original)

        for error in self.get_all_errors():

            if self.normalize_original(error["original"]) == original:

                return error

        return None

    def get_error_frequency(self, original):
        error = self.find_error(original)
        return error.get("count", 0) if error else 0

    def match_current_error(self, original):
        return self.find_error(original)

    # ========================================
    # Generate LLM Memory Context
    # ========================================

    def get_llm_context(
        self,
        limit=5
    ):

        errors = self.get_important_errors(
            limit=limit
        )

        if not errors:

            return (
                "No previous speaking errors "
                "have been recorded."
            )

        lines = []

        lines.append(
            "KNOWN LEARNER ERRORS:"
        )

        lines.append("")

        for index, error in enumerate(
            errors,
            start=1
        ):

            lines.append(
                f"{index}. "
                f"{error['original']} "
                f"→ "
                f"{error['better']}"
            )

            lines.append(
                f"   category: "
                f"{error['category']}"
            )

            lines.append(
                f"   frequency: "
                f"{error['count']}"
            )

            lines.append("")

        lines.append(
            "Pay special attention to repeated "
            "errors, but do not force corrections "
            "when they are irrelevant to the "
            "current conversation."
        )

        return "\n".join(lines)

    # ========================================
    # Print Memory
    # ========================================

    def print_memory(self):

        errors = self.get_all_errors()

        print()
        print(
            "══════════════════════════════════"
        )

        print(
            "          Error Memory"
        )

        print(
            "══════════════════════════════════"
        )

        if not errors:

            print()
            print(
                "No errors recorded yet."
            )

        else:

            for index, error in enumerate(
                errors,
                start=1
            ):

                print()

                print(
                    f"{index}. "
                    f"{error['original']}"
                )

                print(
                    f"   → "
                    f"{error['better']}"
                )

                print(
                    f"   Category: "
                    f"{error['category']}"
                )

                print(
                    f"   Severity: "
                    f"{error['severity']}"
                )

                print(
                    f"   Count: "
                    f"{error['count']}"
                )

        print()

        print(
            "══════════════════════════════════"
        )
