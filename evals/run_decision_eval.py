#!/usr/bin/env python3
"""决策链规格符合性评测（Decision Conformance Evaluation）。

对 Agent 决策链的确定性部分做两类检查：

1. 场景符合性：45 条标注场景跑通 PriorityEngine + InterventionPolicy，与期望动作/等级比对，
   输出准确率、各动作 precision/recall/F1 与混淆矩阵。
   期望值来自 docs/AGENT_SPEC.md 与 docs/AGENT_ARCHITECTURE.md 的明文约定。

2. 规格不变量：直接来自规格文档的硬性保证，用探针矩阵逐条验证，例如
   「ASR uncertain 不等于 English error」「不得发现错误就直接练习」。

用法：
    python -m evals.run_decision_eval
    python -m evals.run_decision_eval --json results.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Windows 控制台默认不是 UTF-8，中文报告会乱码
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):  # pragma: no cover
            pass

from app.application.intervention_policy import InterventionPolicy  # noqa: E402
from app.application.priority_engine import PriorityEngine  # noqa: E402
from app.coach import Correction, NaturalnessSuggestion  # noqa: E402
from app.domain.evidence import ErrorEvidence, Evidence, NaturalnessEvidence  # noqa: E402
from app.domain.intervention import InterventionType  # noqa: E402
from app.domain.observation import Observation  # noqa: E402
from app.domain.priority import PRIORITY_HIGH_THRESHOLD, PRIORITY_MEDIUM_THRESHOLD  # noqa: E402

SCENARIO_FILE = Path(__file__).resolve().parent / "data" / "decision_scenarios.jsonl"

ERROR_SIGNAL_KEYS = (
    "current_error_detected", "historical_match", "historical_frequency",
    "user_requested", "asr_uncertain", "recently_practiced",
)
NATURALNESS_SIGNAL_KEYS = (
    "current_naturalness_detected", "historical_match", "historical_frequency",
    "user_requested", "asr_uncertain", "recently_practiced",
)


# --------------------------------------------------------------------------- #
# 场景构造
# --------------------------------------------------------------------------- #
def build_observation(raw: Dict[str, Any]) -> Observation:
    return Observation(
        session_id="eval-session",
        turn_id=1,
        phase="conversation",
        user_text=raw.get("user_text") or "",
        correction=Correction(
            needed=raw.get("correction_original") is not None,
            original=raw.get("correction_original"),
        ),
        naturalness=NaturalnessSuggestion(
            detected=raw.get("naturalness_original") is not None,
            original=raw.get("naturalness_original"),
        ),
        is_valid=raw.get("is_valid", True),
    )


def build_evidence(raw: Dict[str, Any]) -> Evidence:
    err = {k: v for k, v in (raw.get("error") or {}).items() if k in ERROR_SIGNAL_KEYS}
    nat = {k: v for k, v in (raw.get("naturalness") or {}).items() if k in NATURALNESS_SIGNAL_KEYS}
    return Evidence(error=ErrorEvidence(**err), naturalness=NaturalnessEvidence(**nat))


def load_scenarios(path: Path = SCENARIO_FILE) -> List[Dict[str, Any]]:
    cases = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            cases.append(json.loads(line))
        except json.JSONDecodeError as exc:  # pragma: no cover - 数据错误时给出定位
            raise SystemExit(f"{path.name}:{lineno} JSON 解析失败：{exc}") from exc
    return cases


# --------------------------------------------------------------------------- #
# 决策执行
# --------------------------------------------------------------------------- #
class DecisionRunner:
    """把一次事实输入跑完整条确定性决策链。"""

    def __init__(self) -> None:
        self.priority_engine = PriorityEngine()
        self.intervention_policy = InterventionPolicy()

    def run(self, observation: Observation, evidence: Evidence, mode: str,
            context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        context = dict(context or {})
        priority = self.priority_engine.evaluate(observation, evidence, context)
        decision = self.intervention_policy.decide(
            observation, evidence, priority, mode=mode, session_context=context,
        )
        return {
            "action": decision.type.value,
            "task": bool(decision.should_create_task),
            "priority_type": priority.target_type if priority else None,
            "level": priority.level.value if priority else None,
            "score": round(priority.score, 4) if priority else None,
            "reasons": list(priority.reasons) if priority else [],
        }


def evaluate_scenarios(runner: DecisionRunner,
                       cases: Iterable[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    action_ok = task_ok = level_ok = type_ok = 0
    confusions: Dict[Tuple[str, str], int] = defaultdict(int)
    per_action: Dict[str, Dict[str, int]] = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})

    for case in cases:
        observation = build_observation(case["observation"])
        evidence = build_evidence(case["evidence"])
        actual = runner.run(observation, evidence, case.get("mode", "foreign_friend"), case.get("context"))
        expect = case["expect"]

        checks = {
            "action": actual["action"] == expect["action"],
            "task": actual["task"] == expect["task"],
            "priority_type": actual["priority_type"] == expect["priority_type"],
            "level": actual["level"] == expect["level"],
        }
        action_ok += checks["action"]
        task_ok += checks["task"]
        type_ok += checks["priority_type"]
        level_ok += checks["level"]
        confusions[(expect["action"], actual["action"])] += 1

        for label in {expect["action"], actual["action"]}:
            if label == expect["action"] == actual["action"]:
                per_action[label]["tp"] += 1
            elif label == expect["action"]:
                per_action[label]["fn"] += 1
            else:
                per_action[label]["fp"] += 1

        results.append({
            "id": case["id"], "group": case.get("group", ""), "spec": case.get("spec", ""),
            "note": case.get("note", ""), "mode": case.get("mode"),
            "expected": expect, "actual": actual, "checks": checks,
            "passed": all(checks.values()),
        })

    total = len(results) or 1
    metrics = {
        "total": len(results),
        "action_accuracy": action_ok / total,
        "task_accuracy": task_ok / total,
        "priority_type_accuracy": type_ok / total,
        "level_accuracy": level_ok / total,
        "per_action": {},
        "confusion": {f"{e}->{a}": n for (e, a), n in sorted(confusions.items())},
    }
    for label, c in sorted(per_action.items()):
        tp, fp, fn = c["tp"], c["fp"], c["fn"]
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        metrics["per_action"][label] = {
            "precision": precision, "recall": recall, "f1": f1,
            "support": tp + fn,
        }
    return results, metrics


# --------------------------------------------------------------------------- #
# 规格不变量（独立于实现，直接来自 docs/AGENT_SPEC.md 的明文保证）
# --------------------------------------------------------------------------- #
def _probe(mode: str, *, kind: str, freq: int = 0, hist: bool = False,
           requested: bool = False, asr: bool = False, practiced: bool = False,
           context: Optional[Dict[str, Any]] = None) -> Tuple[Observation, Evidence, str, Dict[str, Any]]:
    observation = build_observation({
        "user_text": "probe",
        "is_valid": True,
        "correction_original": "I very like" if kind == "error" else None,
        "naturalness_original": "very delicious" if kind == "naturalness" else None,
    })
    payload = {
        "current_error_detected": kind == "error",
        "current_naturalness_detected": kind == "naturalness",
        "historical_match": hist,
        "historical_frequency": freq,
        "user_requested": requested,
        "asr_uncertain": asr,
        "recently_practiced": practiced,
    }
    evidence = build_evidence({
        "error": payload if kind == "error" else {},
        "naturalness": payload if kind == "naturalness" else {},
    })
    return observation, evidence, mode, dict(context or {})


def check_invariants(runner: DecisionRunner) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    modes = ("foreign_friend", "teacher", "business_coach")
    kinds = ("error", "naturalness")

    def record(name: str, spec: str, ok: bool, detail: str) -> None:
        findings.append({"invariant": name, "spec": spec, "ok": ok, "detail": detail})

    # INV-1 / §7：ASR 不确定不得触发打断，也不得建任务
    violations = []
    for mode in modes:
        for kind in kinds:
            for freq in (0, 3, 5):
                obs, ev, m, ctx = _probe(mode, kind=kind, freq=freq, hist=True,
                                         requested=False, asr=True)
                out = runner.run(obs, ev, m, ctx)
                if out["action"] == InterventionType.INTERRUPT.value or out["task"]:
                    violations.append(f"{mode}/{kind}/freq={freq} -> {out['action']}, task={out['task']}")
    record("ASR 不确定不介入", "AGENT_SPEC §7", not violations,
           "无违例" if not violations else "; ".join(violations))

    # INV-2 / §9：不得「发现错误就直接练习」——建任务必须由用户显式请求触发
    violations = []
    for mode in modes:
        for kind in kinds:
            for freq in (0, 2, 3, 5):
                for hist in (False, True):
                    obs, ev, m, ctx = _probe(mode, kind=kind, freq=freq, hist=hist,
                                             requested=False, asr=False)
                    out = runner.run(obs, ev, m, ctx)
                    if out["task"]:
                        violations.append(f"{mode}/{kind}/freq={freq}/hist={hist} 未请求却建任务")
    record("未请求不建任务", "AGENT_SPEC §9", not violations,
           "无违例" if not violations else "; ".join(violations))

    # INV-3 / §5：单次错误不得自动成为 high
    violations = []
    for mode in modes:
        obs, ev, m, ctx = _probe(mode, kind="error", freq=0, hist=False, requested=False)
        out = runner.run(obs, ev, m, ctx)
        if out["level"] == "high":
            violations.append(f"{mode} 单次错误被判为 high (score={out['score']})")
    record("单次错误不高优先级", "AGENT_SPEC §5", not violations,
           "无违例" if not violations else "; ".join(violations))

    # INV-4 / §5：首次自然表达信号不得自动成为 high
    violations = []
    for mode in modes:
        obs, ev, m, ctx = _probe(mode, kind="naturalness", freq=0, hist=False, requested=False)
        out = runner.run(obs, ev, m, ctx)
        if out["level"] == "high":
            violations.append(f"{mode} 首次自然表达被判为 high (score={out['score']})")
    record("首次自然表达不高优先级", "AGENT_SPEC §5", not violations,
           "无违例" if not violations else "; ".join(violations))

    # INV-5：score 恒在 [0, 1]
    violations = []
    for mode in modes:
        for kind in kinds:
            for freq in (0, 3, 10):
                for hist in (False, True):
                    for requested in (False, True):
                        for asr in (False, True):
                            for practiced in (False, True):
                                obs, ev, m, ctx = _probe(mode, kind=kind, freq=freq, hist=hist,
                                                         requested=requested, asr=asr, practiced=practiced)
                                out = runner.run(obs, ev, m, ctx)
                                score = out["score"]
                                if score is None or not (0.0 <= score <= 1.0):
                                    violations.append(f"{mode}/{kind}/freq={freq} score={score}")
    record("优先级分数落在 [0,1]", "AGENT_SPEC §5", not violations,
           "无违例" if not violations else "; ".join(violations[:3]))

    # INV-6 / §5：ASR 不确定性应降低同一输入的错误优先级
    violations = []
    for mode in modes:
        for freq in (1, 3, 5):
            base_obs, base_ev, m, ctx = _probe(mode, kind="error", freq=freq, hist=True, asr=False)
            asr_obs, asr_ev, _, _ = _probe(mode, kind="error", freq=freq, hist=True, asr=True)
            base = runner.run(base_obs, base_ev, m, ctx)["score"]
            damped = runner.run(asr_obs, asr_ev, m, ctx)["score"]
            if base is not None and damped is not None and damped >= base:
                violations.append(f"{mode}/freq={freq}: {base} -> {damped} 未下降")
    record("ASR 不确定性降低优先级", "AGENT_SPEC §5", not violations,
           "无违例" if not violations else "; ".join(violations))

    # INV-7 / ARCHITECTURE §4：决策链无副作用，重复调用结果一致
    violations = []
    for mode in modes:
        for kind in kinds:
            obs, ev, m, ctx = _probe(mode, kind=kind, freq=3, hist=True, requested=True)
            first = runner.run(obs, ev, m, ctx)
            second = runner.run(obs, ev, m, ctx)
            if first != second:
                violations.append(f"{mode}/{kind} 两次结果不一致")
    record("决策链无副作用", "AGENT_ARCHITECTURE §4", not violations,
           "无违例" if not violations else "; ".join(violations))

    # INV-8：system_error 上下文必须保持 CONTINUE
    violations = []
    for mode in modes:
        for kind in kinds:
            obs, ev, m, ctx = _probe(mode, kind=kind, freq=5, hist=True, requested=True,
                                     context={"system_error": True})
            out = runner.run(obs, ev, m, ctx)
            if out["action"] != InterventionType.CONTINUE.value:
                violations.append(f"{mode}/{kind} -> {out['action']}")
    record("system_error 保持安全态", "AGENT_ARCHITECTURE §2", not violations,
           "无违例" if not violations else "; ".join(violations))

    return findings


# --------------------------------------------------------------------------- #
# 报告
# --------------------------------------------------------------------------- #
def print_report(results: List[Dict[str, Any]], metrics: Dict[str, Any],
                 invariants: List[Dict[str, Any]]) -> None:
    failures = [r for r in results if not r["passed"]]
    line = "=" * 74
    print(line)
    print("决策链规格符合性评测")
    print(line)
    print(f"场景数        : {metrics['total']}")
    print(f"动作准确率    : {metrics['action_accuracy']:.1%}")
    print(f"建任务准确率  : {metrics['task_accuracy']:.1%}")
    print(f"目标类型准确率: {metrics['priority_type_accuracy']:.1%}")
    print(f"优先级准确率  : {metrics['level_accuracy']:.1%}")

    print("\n各动作 precision / recall / F1")
    for label, m in metrics["per_action"].items():
        print(f"  {label:<20} P={m['precision']:.2f}  R={m['recall']:.2f}  "
              f"F1={m['f1']:.2f}  n={m['support']}")

    print("\n混淆矩阵（期望 -> 实际）")
    for pair, n in metrics["confusion"].items():
        marker = "" if pair.split("->")[0] == pair.split("->")[1] else "   <-- 不一致"
        print(f"  {pair:<34} {n}{marker}")

    print("\n规格不变量")
    for item in invariants:
        mark = "PASS" if item["ok"] else "FAIL"
        print(f"  [{mark}] {item['invariant']}  ({item['spec']})")
        if not item["ok"]:
            print(f"         {item['detail']}")

    if failures:
        print("\n不符合规格的场景")
        for r in failures:
            print(f"  {r['id']}  [{r['group']}]  {r['spec']}")
            print(f"     {r['note']}")
            print(f"     期望 {r['expected']}")
            print(f"     实际 {r['actual']}")

    print("\n" + line)
    inv_failed = [i for i in invariants if not i["ok"]]
    print(f"场景符合性 {metrics['total'] - len(failures)}/{metrics['total']} 通过；"
          f"不变量 {len(invariants) - len(inv_failed)}/{len(invariants)} 通过")
    print(line)


def main() -> int:
    parser = argparse.ArgumentParser(description="决策链规格符合性评测")
    parser.add_argument("--json", dest="json_out", help="把结果写入 JSON 文件")
    args = parser.parse_args()

    runner = DecisionRunner()
    cases = load_scenarios()
    results, metrics = evaluate_scenarios(runner, cases)
    invariants = check_invariants(runner)
    print_report(results, metrics, invariants)

    if args.json_out:
        Path(args.json_out).write_text(json.dumps({
            "metrics": metrics, "invariants": invariants, "results": results,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n结果已写入 {args.json_out}")

    failures = [r for r in results if not r["passed"]]
    inv_failed = [i for i in invariants if not i["ok"]]
    return 1 if failures or inv_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
