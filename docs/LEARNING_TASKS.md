# Learning Task Model

## 1. Purpose

Learning Task 是长期学习型 Agent 用来表示“用户当前正在解决什么问题”的持久学习对象。本文件定义其概念、边界、生命周期和实现约束。当前 Task I 将现有 `LearningTask`、`TaskManager` 与 Decision Loop 连接起来，但不实现 Outcome Loop、自动 Evaluation、复杂 Goal Engine 或 V0.4。

Agent 的闭环应逐步形成：

```text
Conversation -> Observation -> Evidence -> Priority
-> Intervention -> Task candidate / Active Task match
-> Action hint -> Learning Task
-> Training -> Evaluation -> Progress -> Completion
-> Long-term Goal -> 下一轮 Conversation
```

不是每个 Observation、Priority 或 Intervention 都会产生 Task。

## 2. Long-term Goals

Long-term Goal 是持续数月甚至更久的学习方向，例如 `Natural Expression`、`Vocabulary Richness`、`Communication Clarity`、`Speaking Confidence`、`Business English` 或 `Opinion Expression`。

它不会因为一次错误或一个 Task 完成而消失，可以持续拥有多个 Short-term Task，并保存方向性 progress。Task 完成后，Goal 仍然存在；Agent 可以根据新 Evidence 创建下一项具体任务。

Long-term Goal 表示“长期想发展哪种能力”，而 Short-term Task 表示“当前要改善哪一个可验证的问题”。本 Task 不定义 Long-term Goal 的独立数据模型，只保留 `long_term_goal_id` 关联点。

## 3. Short-term Tasks

Short-term Task 是一个跨 Session、有限范围、可训练并可验证的学习目标，例如：

> Practice expressing opinions without repeatedly using “I think”.

Task 必须有明确目标、来源、状态、优先级、证据关联和 Success Criteria。它不是一次练习流程，也不是一次 Session 的计划。

### Task 与 Targeted Practice

Targeted Practice 是执行 Task 的一种 Action，当前实现的 `correction -> repetition -> variation -> free_use` 只是一次专项练习流程。一个 Task 可以通过 Targeted Practice、正常 Conversation 中的隐式练习、下一次 Session 的专项训练或 Review 来推进。

因此：

```text
Learning Task -> 可选择 Targeted Practice
```

Targeted Practice 完成只代表一次训练活动完成，不代表用户已经改善，不能自动把 Task 标为 `completed`。

## 4. Task Lifecycle

状态保持最小集合，并且每个状态都必须改变 Agent 的行为：

| 状态 | 含义与 Agent 行为 |
|---|---|
| `proposed` | Agent 或用户提出了候选目标，尚未得到用户同意；Agent 可以解释和询问，但不应把它当成用户已接受的主动训练承诺。 |
| `accepted` | 用户明确同意；任务已进入用户的学习范围，可安排训练，但尚未必开始。 |
| `active` | 当前仍需解决；跨 Session 保持可见，可被 Session 计划和 Agent 决策考虑。 |
| `practicing` | 正在某次活动中执行训练；离开该活动后若未满足标准，回到 `active`。 |
| `review` | 已收集足够训练结果，正在检查是否满足 Success Criteria；不能仅凭练习步骤进入完成。 |
| `completed` | Evaluation 根据 Success Criteria 判断已达到目标；保留历史和证据，不再作为普通 active task 推送。 |
| `paused` | 用户暂缓、当前不适合继续或长期无进展；保留历史，不主动安排，允许恢复。 |
| `cancelled` | 用户拒绝或明确取消；保留记录，不应立即重复提出同一任务。 |

推荐主路径为 `proposed -> accepted -> active -> practicing -> review -> completed`。允许 `active -> paused`、`practicing -> paused`、`paused -> active`。用户拒绝时为 `proposed -> cancelled`。练习未达标时从 `review` 回到 `active`，而不是标记失败；本阶段不另设 `failed` 状态。

## 5. Task Creation

### 用户主动提出

用户说 “I want to improve my vocabulary.” 时，可以快速创建 `proposed` Task，并询问是否纳入训练目标。明确接受后进入 `accepted`，随后在适当时机进入 `active`。用户主动表达提高了候选任务的可信度和优先级，但仍需形成可执行的短期描述。

### Agent 自动发现

Agent 不能仅依据 `frequency >= 3` 创建 Task。至少应综合可靠 Evidence、PriorityResult 和当前 Context：问题是否真实而非 ASR 不确定、是否重复或影响沟通、是否与用户 Goal/Session 相关、是否值得投入训练，以及是否已有覆盖它的任务。通过后先创建 `proposed` 并征求同意；不强迫用户接受长期专项训练。

严重 Communication Problem 可以触发即时 `interrupt` 或短期修正，但这只是当前 Intervention。是否创建长期 Task 仍应单独判断并尊重用户意愿。

低价值、一次性问题只进入 Memory 或当前反馈，不创建 Task。

### Session Review

Session Review 不是 Task。它可以汇总 repeated patterns、communication issues 和用户请求，并生成 `recommended_short_term_tasks`。推荐项仍是候选，用户接受后才成为 `accepted` Task；拒绝则为 `cancelled`。

## 6. Task Priority

Task 保存 `low`、`medium` 或 `high`，沿用现有 `PriorityLevel` 的枚举值。Task priority 表示“这个已存在任务当前值得投入多少学习资源”，可以随新的 Evidence 和任务状态更新。

`PriorityEngine` 的 PriorityResult 则回答“当前 Observation 中哪个信号最值得关注”，包含 0.0 到 1.0 的 score、level、reasons 和 target。前者是跨 Session 的任务调度属性，后者是当前 Turn 的分析结果；Task priority 可以参考 PriorityResult，但不能复制其评分逻辑，也不能形成第二套独立优先级系统。

## 7. Task Sources

`source` 至少支持：

| source | 含义 |
|---|---|
| `user_requested` | 用户主动提出需求。 |
| `agent_detected` | Agent 根据多项 Evidence 发现模式。 |
| `session_review` | Session Review 汇总后提出。 |
| `long_term_goal` | 为推进既有 Long-term Goal 而提出。 |
| `communication_issue` | 沟通清晰度或理解受到实际影响。 |

Source 解释 Task 为什么存在，不等于当前优先级，也不等于 Intervention 类型。

## 8. Minimal Task Data Model

未来实现的最小数据模型建议如下。字段是概念契约，不是本阶段的 Python 类：

| 字段 | 必需 | 用途 |
|---|---:|---|
| `task_id` | 是 | 跨 Session 稳定识别、去重和引用。 |
| `title` | 是 | 短标题，便于 Agent 和用户扫描。 |
| `description` | 是 | 具体、可执行的训练目标，避免只有语法标签。 |
| `source` | 是 | 记录创建原因。 |
| `status` | 是 | 控制生命周期和 Agent 行为。 |
| `priority` | 是 | 表示当前任务资源优先级。 |
| `long_term_goal_id` | 否 | 把短期目标归入长期方向；未归类时可为空。 |
| `created_at` | 是 | 保留创建时间和历史顺序。 |
| `accepted_at` | 否 | 记录用户同意时间，区分提议和承诺。 |
| `started_at` | 否 | 记录首次真正进入训练的时间。 |
| `completed_at` | 否 | 记录通过 Evaluation 的时间。 |
| `related_observations` | 否 | 引用支持或验证 Task 的 Observation，便于追溯。 |
| `related_evidence` | 否 | 引用聚合证据，避免任务脱离依据。 |
| `success_criteria` | 是 | 描述什么算改善，由未来 Evaluation 判断。 |
| `progress` | 是 | 保存概念化进度摘要，不要求当前计算复杂指标。 |

引用应指向已有记录或稳定 ID，不应把完整 transcript 嵌入 Task。时间统一使用可序列化时间值；创建后应保留审计历史。

## 9. Success Criteria

Success Criteria 是目标描述，不是当前阶段的统计算法。例如 “Improve past-tense storytelling” 可以定义为：连续 3 次相关表达正确、一次完整故事中正确使用过去时，或错误频率明显下降。

Criteria 应尽量描述可观察行为、适用上下文和达到标准。未来由 Agent 或 Learning Evaluation Engine 综合多个 Session 的 Evidence 判断。一次 Targeted Practice 完成、一次正确回答或四步流程结束，都不足以单独证明 Task 完成。

真正的“改善”是：在相关上下文中，目标行为比创建 Task 时更稳定，且改善具有足够重复或覆盖范围，并符合该 Task 的 Success Criteria；不是暂时记住了一个答案。

## 10. Progress

Progress 是 Task 的学习状态摘要，不等于 `practice_step / 4`。至少应能表达以下概念：`observation_count`、`practice_count`、`successful_uses`、`recurrence` 和 `improvement`。这些可以是未来的结构化字段或评估输入，本阶段不规定复杂计算、阈值或统计引擎。

Targeted Practice、隐式 Conversation 和 Review 都可以贡献 Progress。练习次数增加但 recurrence 未下降时，Task 仍可保持 `active`。

## 11. Memory Relationship

Memory 记录“用户过去发生过什么”，Task 记录“用户现在正在解决什么”。例如 Memory 可以保存 `interested in -> interesting in` 的 frequency=5；Task 可以是“Improve adjective/participle usage in common expressions”。

Task 关联 Memory/Evidence，但不替代它们。Task 完成、暂停或取消后，Memory、LearningEvent 和历史证据都不删除；未来评估仍可使用它们。ASR 不确定的信号也不能绕过现有规则直接成为错误 Memory 或 Task 依据。

## 12. Session Relationship

Session 是一次训练活动，Task 是跨 Session 的学习目标。Task 不绑定单个 Session，只引用相关 Observation/Evidence 和可选的活动记录：Session 1 发现并提议，Session 2 训练，Session 3 验证，Session 4 完成。Session 结束可以产生 Review 和下一次建议，但不能结束 Task 的生命周期。

## 13. Coach Mode Relationship

Coach Mode 不改变 Task 本身的目标、所有权或历史。它只影响是否主动提出、解释方式、训练密度和 Review 时机：`foreign_friend` 更少主动提议，`teacher` 更积极，`business_coach` 更重视商务沟通相关任务。模式变化不应复制 Task 或篡改其来源。

## 14. Intervention Relationship

Intervention 回答“现在要不要介入”；Task 回答“我们要解决什么”。流程可以是 `Observation -> Priority -> Intervention -> 可能创建 Task`，但一次 `interrupt`、`light_feedback`、`review_later` 或 `continue` 都不自动等于创建 Task。现有 `should_create_task` 应被理解为候选创建信号。Task I 可以消费该信号并调用 TaskManager 创建 `proposed` Task，但不得自动转为 `accepted`；去重仍由 TaskManager 负责，用户同意仍是独立步骤。

## 15. Duplicate Prevention

创建前必须按稳定目标概念、Long-term Goal、未完成任务和近期历史检查重复。已有 `proposed`、`accepted`、`active`、`practicing`、`review` 或 `paused` 任务覆盖同一问题时，应更新证据或 progress，而不是创建新任务。已 `completed` 或 `cancelled` 的同类问题也不能立刻重建；应重新评估新的 Evidence、间隔和上下文，必要时作为重新打开原任务或创建明确的新版本。

默认每个 Long-term Goal 同时最多保持 1 个 `practicing` Task，建议最多 3 个 `active`/`accepted` Task。超过上限时先排序、暂停或排队，而不是继续累积几十个任务。该上限是行为约束，未来可由用户设置覆盖。

## 16. Reopening Tasks

`paused` Task 在用户重新同意或新的高可信 Evidence 表明仍值得继续时可回到 `active`。`completed` Task 只有在新的、明确不同的回归证据出现，且重新评估确认原 Success Criteria 不再稳定时才可重新打开；应保留原完成记录并记录 reopen reason。`cancelled` Task 默认不自动复活，除非用户再次明确提出或明确同意重新训练。

## 17. Task I Agent Decision Loop

Task I 的职责是把当前 Turn 的学习信号连接成最小可执行决策：

```text
TurnResult -> ObservationBuilder -> Observation + Evidence
-> PriorityEngine -> PriorityResult
-> InterventionPolicy -> InterventionDecision
-> Active Task match / Task candidate / Action hint
```

Task I 可以识别当前问题与已有 `active` Task 的关联，并把该信息提供给后续流程；不自动开始 Targeted Practice。用户主动提出或 Agent 根据可靠、重复、高价值证据提出的候选任务，必须通过 `TaskManager.create_task()` 以 `proposed` 状态持久化。已有相同的 `active` 或 `proposed` Task 时不得重复创建。

SessionReview 可以汇总当前 Session 的高价值 Observation、Evidence 和 Intervention，并产生推荐任务；推荐仍是 candidate，不能绕过 TaskManager，也不能直接成为 `active`。

`system_error` 不进入这条学习链；ASR uncertainty 只能作为 uncertainty evidence，不能单独产生 English error 或 Task。

## 18. Future Learning Loop

每轮 Conversation 产生 Observation 和 Evidence；PriorityEngine 评估当前信号；InterventionPolicy 选择是否继续、反馈、打断、延后或练习；Task Decision 再判断是否创建、关联现有 Task 或只更新 Memory。被接受的 Task 可影响后续 Session 计划和 Action 选择。训练后的 Outcome 更新 Progress，Review 阶段根据 Criteria 决定继续、暂停或完成；完成后回到 Long-term Goal，等待下一轮 Evidence。

## 19. Design Answers

1. Long-term Goal 是长期能力方向；Short-term Task 是当前可验证的具体目标。
2. Targeted Practice 是执行 Task 的一种训练方式，不是跨 Session 的学习对象。
3. 用户主动提出时先创建 `proposed`，询问并在接受后进入 `accepted`。
4. Agent 只有在可靠 Evidence、Priority、Context 和无重复覆盖时提出 Task；不以频率单独触发。
5. 用户拒绝后进入 `cancelled`，保留历史，短期不重复提议。
6. Task 完成后不删除 Memory。
7. Task 跨 Session；Session 只是活动。
8. Coach Mode 影响提议和训练行为，不改变 Task 本身。
9. PriorityEngine 评估当前信号；Task priority 评估已有任务的当前资源优先级。
10. 新的明确回归证据可重新打开已完成任务；暂停任务可在用户或新证据触发下恢复。
11. 通过稳定目标、Goal、未完成任务和历史状态去重，并设置 active 上限。
12. 默认每个 Goal 最多 3 个 active/accepted Task，最多 1 个 practicing Task。
13. Session Review 生成候选推荐，用户接受后才成为 Task。
14. Targeted Practice 完成不自动完成 Task。
15. 真正改善是相关上下文中的稳定行为变化，并满足 Success Criteria。

## 20. Examples

### Example A: Natural Expression

Long-term Goal: `Natural Expression`。Agent 从多次 Evidence 发现 “I think” 重复，提出 `proposed` Task：“Practice expressing opinions with alternatives to ‘I think’.” 用户接受后跨多个 Session 练习、隐式使用并 Review；一次四步 Targeted Practice 完成后仍保持 `active`，直到 Criteria 证实 recurrence 下降。

### Example B: Communication Issue

一次严重表达造成理解风险，Intervention 可以立即 `interrupt` 并给出修正。若后续 Evidence 证实这是稳定问题，Agent 再以 `communication_issue` 创建 `proposed` Task；即时修正本身不等于用户接受了长期任务。

## 21. Current Design Conflicts and Implementation Notes

- `docs/AGENT_ARCHITECTURE.md` 当前把后续层称为 `Learning Goal` 和 `Action Planner`，而本模型引入了更持久的 `Learning Task`。实现时应明确：Long-term Goal/Short-term Task 属于学习状态，Action Planner 负责选择动作，不能把三者合并。
- `docs/ROADMAP.md` 保留 Task H `Agent Loop / Outcome`；Task I 只负责最小 Decision Loop 的连接，不吸收 Outcome、自动 Evaluation 或完成判断。
- 当前 `InterventionDecision.should_create_task` 和 `SessionReview.recommended_short_term_tasks` 仍是信号/推荐结构；Task I 通过 TaskManager 将它们转换为 `proposed` Task，但不自动接受、激活或完成。
- 当前 Router 可依据当前 Session 内频率切换 `targeted_practice`，这表示活动路由，不表示 Task 已创建、已接受或已完成。
- 当前 `LearningEvent` 有 `PRACTICE_STARTED`/`PRACTICE_COMPLETED` 类型，但 `LearningUpdateService` 尚未建立 Task 关联或 Outcome Evaluation；未来实现必须避免把事件类型直接当作 Task 状态机。

Task I 实现时最需要注意：保持状态转换、用户同意、唯一性/去重、跨 Session 持久化和可追溯引用边界；不要让一次练习步骤、一次 Intervention 或单次错误直接改变 Task 的长期结论。Progress/Evaluation 和 Outcome Loop 留给 Task H 及后续阶段。
