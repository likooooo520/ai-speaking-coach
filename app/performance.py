import json
from pathlib import Path


class PerformanceTracker:

    def __init__(
        self,
        file_path="data/performance.json"
    ):

        self.file_path = Path(file_path)

        self.file_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.data = {
            "current_difficulty": "B2",
            "recent_performance": [],
            "strong_streak": 0,
            "weak_streak": 0,
            "sessions": 0
        }

        self.load()

    # ========================================
    # Load
    # ========================================

    def load(self):

        if not self.file_path.exists():

            self.save()

            return

        try:

            with open(
                self.file_path,
                "r",
                encoding="utf-8"
            ) as f:

                loaded = json.load(f)

            self.data.update(loaded)

        except Exception as e:

            print()
            print("⚠️ Performance Memory 读取失败")
            print(f"错误：{e}")
            print()

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
            print("⚠️ Performance Memory 保存失败")
            print(f"错误：{e}")
            print()

    # ========================================
    # Record
    # ========================================

    def record(
        self,
        performance,
        suggested_action
    ):

        band = performance.get(
            "band",
            "normal"
        )

        entry = {
            "band": band,
            "fluency": performance.get(
                "fluency",
                0
            ),
            "grammar": performance.get(
                "grammar",
                0
            ),
            "vocabulary": performance.get(
                "vocabulary",
                0
            ),
            "naturalness": performance.get(
                "naturalness",
                0
            ),
            "overall": performance.get(
                "overall",
                0
            ),
            "suggested_action": suggested_action
        }

        self.data[
            "recent_performance"
        ].append(entry)

        # 只保留最近 10 轮
        self.data[
            "recent_performance"
        ] = self.data[
            "recent_performance"
        ][-10:]

        self.data["sessions"] += 1

        if band == "strong":

            self.data[
                "strong_streak"
            ] += 1

            self.data[
                "weak_streak"
            ] = 0

        elif band == "weak":

            self.data[
                "weak_streak"
            ] += 1

            self.data[
                "strong_streak"
            ] = 0

        else:

            self.data[
                "strong_streak"
            ] = 0

            self.data[
                "weak_streak"
            ] = 0

        self.save()

    # ========================================
    # Adjust Difficulty
    # ========================================

    def adjust_difficulty(self):

        current = self.data.get(
            "current_difficulty",
            "B2"
        )

        strong_streak = self.data.get(
            "strong_streak",
            0
        )

        weak_streak = self.data.get(
            "weak_streak",
            0
        )

        difficulty_order = [
            "B1",
            "B2",
            "B2+",
            "C1"
        ]

        current_index = (
            difficulty_order.index(current)
            if current in difficulty_order
            else 1
        )

        action = "maintain"

        # ------------------------------------
        # 连续 3 次 strong
        # ------------------------------------

        if strong_streak >= 3:

            if current_index < (
                len(difficulty_order) - 1
            ):

                current_index += 1

                current = (
                    difficulty_order[
                        current_index
                    ]
                )

                action = "increase"

            # 防止一直累积
            self.data[
                "strong_streak"
            ] = 0

        # ------------------------------------
        # 连续 2 次 weak
        # ------------------------------------

        elif weak_streak >= 2:

            if current_index > 0:

                current_index -= 1

                current = (
                    difficulty_order[
                        current_index
                    ]
                )

                action = "decrease"

            self.data[
                "weak_streak"
            ] = 0

        self.data[
            "current_difficulty"
        ] = current

        self.save()

        return current, action

    # ========================================
    # Current Difficulty
    # ========================================

    def get_current_difficulty(self):

        return self.data.get(
            "current_difficulty",
            "B2"
        )

    # ========================================
    # Get Summary
    # ========================================

    def get_summary(self):

        return {
            "current_difficulty":
                self.get_current_difficulty(),

            "strong_streak":
                self.data.get(
                    "strong_streak",
                    0
                ),

            "weak_streak":
                self.data.get(
                    "weak_streak",
                    0
                ),

            "sessions":
                self.data.get(
                    "sessions",
                    0
                )
        }

    # ========================================
    # Print
    # ========================================

    def print_status(self):

        summary = self.get_summary()

        print()
        print(
            "══════════════════════════════════"
        )

        print(
            "       Difficulty Status"
        )

        print(
            "══════════════════════════════════"
        )

        print(
            f"Current difficulty: "
            f"{summary['current_difficulty']}"
        )

        print(
            f"Strong streak: "
            f"{summary['strong_streak']}"
        )

        print(
            f"Weak streak: "
            f"{summary['weak_streak']}"
        )

        print(
            f"Recorded turns: "
            f"{summary['sessions']}"
        )

        print(
            "══════════════════════════════════"
        )