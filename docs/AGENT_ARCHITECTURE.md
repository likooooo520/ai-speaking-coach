# Agent Architecture

## 1. 当前实现

当前代码已经具备一条“分析并更新学习状态”的基础链路：

```text
TurnContext
  -> TurnProcessor
  -> Coach
  -> TurnResult
  -> ObservationBuilder
  -> Observation + Evidence
  -> PriorityEngine
  -> PriorityResult
  -> LearningUpdateService
  -> Error Memory / Naturalness Memory / Performance
```

`TurnContext` 描述 Session、Turn、phase、用户输入、topic 和练习上下文。`TurnProcessor` 将上下文交给 Coach 并包装为 `TurnResult`。`TurnResult` 暴露回复、correction、ASR uncertainty、naturalness、performance、topic、difficulty 和 next action 等当前结果。

`ObservationBuilder` 只组装当前结果与只读历史匹配事实，不产生副作用。`Observation` 保存本轮事实；`Evidence` 保存当前发现、历史匹配、频率、用户请求、ASR 不确定性、Session relevance 和 interruption cost 等依据。`LearningUpdateService` 对有效结果去重，并将确认的错误、自然表达现象和表现写入长期状态。

## 2. Task I：Minimal Agent Decision Loop

Task I 将已存在的 Agent Core 能力第一次连接成可调用的最小决策链，不新增大规模能力：

```text
TurnResult
  -> ObservationBuilder
  -> Observation + Evidence
  -> PriorityEngine
  -> PriorityResult
  -> InterventionPolicy
  -> InterventionDecision
  -> Task candidate / Action hint / Continue
  -> Session Review candidate
```

Active Tasks 作为只读输入参与决策，用于识别当前问题是否与已有 `active` Task 相关；它不由 PriorityEngine 或 InterventionPolicy 修改。

每个有效 Turn 的最小流程是：

1. `system_error` 直接结束分析，不产生 Observation、Priority、Intervention 或 Task。
2. `ObservationBuilder` 从 `TurnResult` 组装当前事实与 Evidence，不写 Memory。
3. `PriorityEngine` 选择当前最值得关注的信号，不创建 Task、不选择教学动作。
4. `InterventionPolicy` 根据 Priority、Evidence、Coach Mode 和上下文返回 `continue`、`light_feedback`、`interrupt`、`review_later` 或 `targeted_practice`。
5. `should_create_task` 只表示 Task candidate；真正持久化必须经由 `TaskManager.create_task()`，且状态为 `proposed`。
6. `SessionReviewGenerator` 在 Session 结束时汇总高价值观察、重复问题、沟通问题和推荐任务；推荐任务仍必须经由 TaskManager 创建。

Task I 的 Action 只表示当前下一步建议或路由提示，不实现完整 Action Planner、Outcome Loop 或自动 Evaluation。

## 3. 未来目标架构

```text
Input / Data
  -> Perception
  -> Observation Builder
  -> Evidence Builder
  -> Priority Engine
  -> Learning Goal Engine
  -> Action Planner
  -> Coach / Practice / Conversation Action
  -> Outcome Evaluator
  -> Memory Update
  -> Session State
```

### Data 与 Perception

Data 是原始输入、ASR 输出、当前 Session 和历史 Memory。Perception 负责提取可观察信号，不应偷偷做优先级或教学决策。

### Observation / Evidence

Observation 是本轮事实快照；Evidence 是事实为何具有学习意义的依据。两者都应尽量可解释、可测试、可回放，且不直接修改 Memory。

### Reasoning / Decision

PriorityEngine 已作为独立的无副作用模块实现，读取 Observation、Evidence 与可选 Session 上下文，输出可解释的 PriorityResult。它使用确定性权重和集中定义的阈值，不调用 Router 或教学动作。Decision 的后续层才会产出 Learning Goal 和 Agent strategy；不应假设“有 correction 就必须练习”。

### Action Planner

Action Planner 把 Decision 转成动作，例如自然回应、延迟反馈、适度纠正、Targeted Practice、主题转换或继续观察。它负责权衡 interruption cost 和用户体验。

### Outcome / Memory

Outcome 记录用户是否理解、是否完成 repetition/variation/free_use、表现是否改善以及对话是否被打断。Memory Update 只把经过规则验证的结果写入长期状态；ASR 不确定的内容不得直接进入 English Error Memory。

## 4. 依赖与边界

- Observation 不依赖 Priority Engine 的决策结果。
- Evidence 可读取历史事实，但 Builder 不负责写 Memory。
- Priority 读取 Observation、Evidence、Session 和 Memory 的摘要，不直接执行教学。
- Task I 的决策层可以产生有限的 Action hint，但不替代未来的 Learning Goal Engine 或完整 Action Planner。
- TaskManager 是创建和持久化 Task 的唯一边界；InterventionPolicy、PriorityEngine 和 SessionReview 不直接写 Task。
- TargetedPractice 只执行训练，不拥有、接受或完成 Task。
- Outcome 必须反馈给下一轮，但 Outcome Loop 不属于本次 Task I。
- Memory 是长期学习状态，不是完整聊天 transcript 的替代品。

## 5. 当前范围与未完成部分

Observation、Evidence、PriorityEngine、InterventionPolicy、LearningTask、TaskManager、TargetedPractice 和 SessionReview 已作为 Task I 的输入或协作能力。Task I 当前只连接最小 Decision Loop。

Task H - Agent Loop / Outcome 仍保留在路线图中，负责未来的动作结果、效果评估和反馈闭环；本次不提前实现。Learning Goal Engine、复杂 Goal Engine、自动 Evaluation、复杂 embedding、Topic Discovery、动态长期策略、多用户、语音和产品化能力仍属于未来范围。
