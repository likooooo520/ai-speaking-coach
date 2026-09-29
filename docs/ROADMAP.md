# Agent Roadmap

本路线图描述从当前基础链路走向长期自适应 Coach 的方向。

## Phase 1：基础 Agent 语义

- [x] Task A - `TurnContext` / `TurnResult`：定义一次 Turn 的输入上下文与结果边界。
- [x] Task B - `TurnProcessor`：把上下文交给 Coach，并产生统一结果。
- [x] Task C - `LearningUpdateService`：将有效结果转换为学习事件并更新 Memory/Performance。
- [x] Task D - Observation / Evidence：区分本轮事实与支持关注的证据。
- [x] Task E - Priority Engine：根据当前信号、历史匹配与频率、用户请求、ASR uncertainty 和最近训练状态产生可解释的关注优先级。
- [ ] Task F - Learning Goal Engine：将优先关注项转成当前可执行的学习目标。
- [ ] Task G - Action Planner：在自然回应、纠正、延迟反馈和 Targeted Practice 等动作中做选择。
- [ ] Task H - Agent Loop / Outcome：记录动作结果，评估是否有效，并反馈下一轮与长期 Memory。
- [ ] Task I - Minimal Agent Decision Loop：连接 Observation、Evidence、Priority、Intervention、Task 和 Session Review，输出有限的下一步 Action hint。

## Phase 2：主动与长期学习

- Topic Discovery：根据对话、兴趣和历史避免重复并自然切换主题。
- Proactive Teaching：在不破坏自然交流的前提下选择介入时机。
- Session Summary：总结表现、弱点、练习、未解决问题和下一次建议。
- Weakness Engine：从多轮证据中确认稳定弱点，而非把单次错误当结论。
- Long-term Learning Strategy：结合用户目标、历史效果和遗忘情况设计长期训练。

## Phase 3：语音交互

- Voice response
- TTS
- 男声 / 女声
- 更丰富的语音互动

这些能力必须保留当前文字 Coach 的学习语义，不应让语音层绕过 Observation、ASR uncertainty 或 Memory 边界。

## Phase 4：产品化能力

- User settings
- 持久化 preference
- UI
- Multi-user

持久设置至少覆盖纯英文、中英双语、深色/浅色和训练模式，并应与 Learner Profile、Session 策略清晰区分。

## 设计约束

1. 初始等级为 A2，后续根据表现动态调整。
2. 当前重点是 vocabulary、natural expression、vocabulary richness 和 ASR misrecognition detection。
3. Grammar 当前不是主要训练目标，pronunciation 与 fluency 暂不做。
4. 默认 Natural Mode；Coach Mode 和 Intensive Mode 通过介入阈值与训练密度体现差异。
5. ASR uncertainty 不得直接写入 English Error Memory。
6. 不使用“出现一次错误就立即高优先级”的规则。
7. 当前阶段不引入复杂 embedding。
8. Task I 允许使用已有 LearningTask、TaskManager、InterventionPolicy 和 SessionReview 连接最小决策链，但不实现 V0.4。
9. Task I 不实现 Outcome Loop、自动 Evaluation、复杂 Goal Engine、复杂 embedding、多用户或云端能力。

## 阶段完成标准

Task E 已完成，Task I 进入当前开发范围。Task H 不删除，仍负责未来的 Outcome Loop。后续每个 Task 应先补充输入输出、状态变化、失败处理和测试策略，再进入代码实现。
