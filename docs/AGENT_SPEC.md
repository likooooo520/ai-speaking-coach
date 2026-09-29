# AI English Speaking Coach Agent Specification

## 1. 文档目的

本文件定义 AI English Speaking Coach 的产品目标、核心概念、行为原则与未来能力边界。它是设计规格，不是实现任务清单。当前 Phase 1 已包含 Task I：在既有 Agent Core 能力之上建立最小 Agent Decision Loop；本阶段不实现 Outcome Loop、自动 Evaluation、复杂 Goal Engine 或多用户能力。

## 2. 项目定位

本项目要从“LLM 加上一组功能”逐步发展为一个有状态、有记忆、有目标、有策略、有反馈循环的英语口语教练 Agent。它不是普通聊天软件，也不是每句话都检查的 English chatbot。

Agent 的长期目标是：

- 提高用户的自然英语表达能力；
- 主动发现并验证长期弱点；
- 根据当前对话和历史表现调整训练；
- 区分真正的英语问题与 ASR 误识别；
- 允许用户主动声明想练习的领域；
- 在 Session 结束后总结表现，并影响未来教学决策；
- 最终能够根据长期表现自主设计训练。

当前用户画像：初始等级 A2，重点训练 vocabulary、natural expression、vocabulary richness 和 ASR misrecognition detection。Grammar 暂不作为主要目标，pronunciation 与 fluency 暂不做。默认由 Coach 自动发现弱点，但用户可在开始或进行中主动指定弱点。V1 只返回文字；TTS、男声/女声等语音能力属于后续阶段。

## 3. Agent Loop

```text
User Input
  -> Perception / Coach
  -> TurnResult
  -> Observation
  -> Evidence
  -> Priority
  -> Intervention
  -> Active Task match / Task candidate / Continue
  -> Action hint
  -> Coach Response
  -> Outcome / Memory (Task H，暂未纳入 Task I)
  -> 下一轮
```

这是一条因果链，而不是一组可以互相替代的命名。每层职责如下：

| 层 | 它是什么 | 为什么存在 |
|---|---|---|
| Data | 原始输入、历史记录、用户设置等数据 | 为判断提供可追溯材料 |
| Perception | 从输入中提取语言表现、ASR 信号和上下文 | 把原始输入变成可分析信息 |
| Observation | 描述这一轮发生了什么的事实 | 隔离“发生了什么”和“应该做什么” |
| Evidence | 支持关注某个现象的依据 | 让判断可以解释、累计和审计 |
| Reasoning | 综合观察、证据、目标和上下文 | 处理单次信号不足以决定的问题 |
| Decision | 选择当前优先级、学习目标和策略 | 明确 Agent 此刻的意图 |
| Action | 具体教学动作，例如回应、延迟纠正或练习 | 把决策转成用户可感知行为 |
| Outcome | 用户对动作的结果和下一轮反馈 | 判断动作是否有效 |
| Memory | 对未来决策有意义的长期状态 | 让 Agent 记住用户并改变后续行为 |

当前 Phase 1 的最小决策链是：

```text
TurnResult -> Observation -> Evidence -> Priority
-> Intervention -> Task candidate / Continue / Action hint
```

其中 Active Tasks 作为跨 Session 的只读上下文输入，用于识别当前问题是否已有任务覆盖。Task I 负责把当前观察、证据、优先级、介入决策和已有任务连接起来，得出下一步 Action hint；它不实现完整 Learning Goal Engine、Outcome Loop 或自动 Evaluation。Observation 不等于 Decision，Evidence 不等于 Decision，Priority 不等于 Action，Task 也不等于 Targeted Practice。

## 4. Observation 与 Evidence

Observation 回答“这一轮发生了什么”，应尽量保持事实性，包括用户说了什么、是否出现 correction、naturalness issue 或 ASR uncertainty、当前 performance、topic 和 phase。Observation 不负责决定优先级、修改 Memory、调整 Difficulty 或启动 Targeted Practice。

Evidence 回答“为什么值得关注”。错误证据至少可包括 `current_error_detected`、`historical_match`、`historical_frequency`、`user_requested`、`asr_uncertain`；自然表达证据至少可包括 `current_naturalness_detected`、`historical_match`、`historical_frequency`、`user_requested`。未来可扩展其他证据，但当前阶段不引入复杂 embedding。

## 5. Priority 与主动教学

Priority Engine 已实现为无副作用的确定性评分模块。它从 Observation、Evidence 与可选 Session 上下文中回答“什么最值得当前关注”，输出可解释的 `PriorityResult`，包含 target type/key、0.0 至 1.0 的 score、统一的 low/medium/high level 与稳定 reason key。它不选择 Action、不调用 Router、不修改 Memory、Performance、Difficulty 或 Session phase。

Error Priority 以当前错误为前提，综合历史匹配、历史频率、用户主动请求、ASR uncertainty 与最近训练状态。Naturalness Priority 以当前自然表达问题为前提，使用独立但同样可解释的规则；首次自然表达信号不会自动成为 high。ASR uncertainty 本身不会产生 Error Priority，且会降低已有错误信号的优先级；最近已练过只在存在可靠事实时降低优先级。

单次错误不应自动变成高优先级。默认流程是：观察、积累证据、判断重要性、判断是否现在处理、再决定是否介入。目标是像老师一样维护自然交流，而不是像 grammar checker 一样逐项打断。

## 6. 对话模式

| 模式 | 行为 |
|---|---|
| Natural Mode | 默认模式。尽量不中断，记录问题，在合适时机处理，维持自然对话。单次低影响错误不强行教学。 |
| Coach Mode | 适度主动纠正，允许在用户需要时解释并引导一次简短练习。 |
| Intensive Mode | 更积极地纠正、重复和练习，适合明确的集中训练时段。 |

模式只影响介入阈值、回应方式和练习密度，不应绕过 ASR 判断或把 Observation 直接当成 Action。

## 7. ASR 原则

`ASR uncertain` 不等于 `English error`。例如系统怀疑识别结果是“many food”，但用户可能说的是“many foods”时，不能直接将其写入 English Error Memory。未来可结合 Whisper confidence、LLM uncertainty 和 context；当前只保留不确定性信号，不实现复杂融合。

## 8. 用户主动弱点

用户可以在 Session 开始说“I want to work on vocabulary”，也可以在交流中说“I always have trouble expressing this”。未来 UI 可提供手动选择。用户明确表达的需求比普通自动发现的问题拥有更高关注优先级，但仍需结合当前 Session、训练目标、干扰成本和可处理性。

## 9. Memory 与学习闭环

长期 Memory 至少包括 Error Memory、Naturalness Memory 和 Performance；未来可加入 Vocabulary、Topic/Interest、Learning Goal、Preference、Session Summary 等 Memory。Memory 不是聊天记录归档，而是能改变未来教学决策的结构化状态。

Targeted Practice 是 Action 的一种，四步为 `correction -> repetition -> variation -> free_use`。正确关系是 `Priority -> Learning Goal -> Action Planner -> Targeted Practice`，而不是发现错误后直接练习。

## 10. Session、Topic 与 Difficulty

Session 应保存当前训练目标、阶段、topic、学习重点、弱点、已训练内容、Agent strategy、Session outcome 和下一次建议。结束时生成 Session Summary：今日表现、发现的弱点、练习内容、仍存在的问题、下次继续什么，以及可以暂时放下什么。

Topic Discovery 是未来模块：由对话和兴趣自然产生主题，避免历史重复，在合适时转换并保持多元化，当前不实现。

Difficulty 将来应从 PerformanceTracker 内部逻辑发展为 Learner Profile/Adaptive Engine 的能力，依据表现、任务完成度、错误频率、自然表达和词汇能力逐步调整。用户初始等级固定为 A2，未来可动态向 B1、B2、B2+、C1 演进。
