# 决策链规格符合性评测（Decision Conformance Evaluation）

## 1. 为什么不是检索指标

本项目**没有检索组件**：`memory.py` 是 JSON 文件 + 正则归一化的长期错误记忆，没有 embedding、没有向量库。
因此 recall@k、MRR、NDCG 这类检索指标在这里不适用，写出来是虚假指标。

本项目真正有价值的可测点是**决策链**——`Observation → Evidence → Priority → Intervention`
是一套确定性规则系统，行为可以被精确断言，因此适合做**规格符合性评测**。

## 2. 两类检查

### 2.1 场景符合性（`data/decision_scenarios.jsonl`）

43 条标注场景覆盖决策空间：无信号、ASR 不确定性、单次/重复错误、自然表达、
用户主动请求、沟通影响、优先级阈值边界、三种对话模式的对照矩阵。

每条场景声明输入事实与期望结果（动作、是否建任务、优先级目标类型与等级），
期望值来自 `docs/AGENT_SPEC.md` 与 `docs/AGENT_ARCHITECTURE.md` 的明文约定。

输出：动作准确率、各动作 precision/recall/F1、混淆矩阵。

### 2.2 规格不变量（独立于实现）

直接把规格文档里的硬性保证写成探针矩阵，逐条验证。这些不变量**不依赖实现细节**，
是在代码之外的独立约束：

| 不变量 | 规格依据 |
| --- | --- |
| ASR 不确定不介入 | `AGENT_SPEC §7`：ASR uncertain 不等于 English error |
| 未请求不建任务 | `AGENT_SPEC §9`：不得「发现错误就直接练习」 |
| 单次错误不高优先级 | `AGENT_SPEC §5`：单次错误不应自动变成高优先级 |
| 首次自然表达不高优先级 | `AGENT_SPEC §5`：首次自然表达信号不会自动成为 high |
| 优先级分数落在 [0,1] | `AGENT_SPEC §5`：score 为 0.0–1.0 |
| ASR 不确定性降低优先级 | `AGENT_SPEC §5`：ASR uncertainty 会降低已有错误信号 |
| 决策链无副作用 | `AGENT_ARCHITECTURE §4`：Priority/Intervention 为纯函数 |
| system_error 保持安全态 | `AGENT_ARCHITECTURE §2`：system_error 直接结束分析 |

## 3. 运行

```bash
python -m evals.run_decision_eval              # 打印报告，有不一致时退出码为 1
python -m evals.run_decision_eval --json out.json
```

Windows 控制台若中文乱码，先设置 `PYTHONIOENCODING=utf-8`（脚本内已尝试自行重设）。

## 4. 当前结果

```
场景数        : 43
动作准确率    : 100.0%
建任务准确率  : 100.0%
优先级准确率  : 100.0%
规格不变量    : 8/8 PASS
场景符合性    : 43/43
```

首次运行（修复前）为 `40/43`、动作准确率 `97.7%`。评测定位到 3 处与规格不一致的行为（见 §5），
修复后全部通过，且既有 193 个单元测试无回归。

## 5. 评测定位到并已修复的缺陷

这 3 处不是环境问题，是实现与规格的真实偏差，由本评测集首次运行时捕获。

### D1 · 阈值边界受浮点误差影响（`priority_engine`）— 已修复

`0.30 + 0.15 + 0.15 + 0.10 − 0.30` 在 IEEE 754 下等于 `0.39999999999999997`，
小于阈值 `0.40`，于是本该判为 `medium` 的信号被判成 `low`。

```python
s = 0.30 + 0.15 + 0.15 + 0.10 - 0.30   # 0.39999999999999997
s >= 0.40                               # False，期望 True
```

影响：所有落在阈值边界上的权重组合都会降一档，进而改变 `InterventionPolicy` 的介入档位。

**修复**：`PriorityEngine` 新增 `SCORE_PRECISION`，钳位后统一取整再比较等级。

### D2 · `recently_practiced` 在两层之间数据源不一致 — 已修复

`PriorityEngine` 读取 `evidence.error.recently_practiced` 并据此扣 0.15 分；
但 `InterventionPolicy` 只从 `session_context`（或显式入参）读取同一事实，**不读 Evidence**。

后果：当该事实由 `ObservationBuilder` 写入 Evidence 时，「刚练过 → 延后复盘」的守卫
不会触发，反而会创建新的专项训练任务，与「刚练习过不重复介入」的设计意图相悖。

**修复**：`InterventionPolicy` 改为按 `显式入参 > Session 上下文 > Evidence` 的顺序回退，
与 `PriorityEngine` 读取同一份事实。

### D3 · `PriorityEngine` 不检查 `observation.is_valid` — 已修复

无效 Observation 仍会产出 `PriorityResult`（例如 `0.30 / low`）。
动作层由 `InterventionPolicy` 的 `is_valid` 守卫兜住，但优先级本身是无效值，
若后续有消费者直接读取 Priority，会拿到不该存在的信号。

**修复**：`evaluate()` 在入口处对无效 Observation 直接返回 `None`。

## 6. 扩展方式

- 新增场景：在 `data/decision_scenarios.jsonl` 追加一行 JSON，字段见现有条目。
- 新增不变量：在 `check_invariants()` 中追加探针循环，并在上表登记规格依据。
- 接入 CI：`run_decision_eval.py` 在有任一场景不一致或不变量失败时返回退出码 1。
