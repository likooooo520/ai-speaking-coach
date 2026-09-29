# AI Speaking Coach Web UI Specification

## 1. 文档目的

本文档定义 AI English Speaking Coach 第一版 Web UI 的产品、交互与视觉规范。它只描述产品行为和界面边界，不实现 Web UI、API、WebSocket、录音前端或后端适配。

## 2. 产品定位

AI Speaking Coach 是一个以自然英语交流为核心、能够长期记住用户问题并主动设计训练的 AI Speaking Coach。

它不是：

- ChatGPT clone
- 英语考试软件
- Grammar checker
- Dashboard
- LMS
- 数据分析后台

核心体验是：

> “I'm talking to someone.”

而不是：

> “I'm operating an AI system.”

产品原则：

1. Conversation First：先交流，再教学。
2. Minimal Interruption：只有学习价值足够高时才打断。
3. Human-like Interaction：界面响应像真实对话，而不是系统操作流。
4. Adaptive Coaching：根据 Coach Mode、当前问题和长期任务调整介入。
5. Long-term Learning：Session 结束后的 Review 和 Task 比连续纠错更重要。
6. Complexity Hidden From User：Observation、Evidence、Priority 等内部概念不直接暴露。

## 3. 信息架构

```text
Home
├── Start Session
│   └── Conversation
│       └── Targeted Practice
└── Session Review
    └── Task recommendation

Training
├── Active Tasks
├── Proposed / Paused / Completed Tasks
└── Long-term Goals

Settings
```

### 页面优先级

| 优先级 | 页面 | 第一版范围 |
|---|---|---|
| P0 | Home | 必须实现；快速开始和继续训练 |
| P0 | Start Session | 必须实现；最小 Session 设置 |
| P0 | Conversation | 必须实现；产品核心体验 |
| P0 | Session Review | 必须实现；Session 结束反馈 |
| P1 | Targeted Practice | 简化版；支持四步训练和返回对话 |
| P1 | Active Tasks | 简化版；查看、接受和继续任务 |
| P2 | Long-term Goals | 简单列表和任务归属 |
| P2 | Training History | 后续实现 |
| P2 | Advanced Settings | 后续实现 |

第一版不应把 Home 做成数据 Dashboard，也不应在首页展示大量分数、图表或技术指标。

## 4. Home

### 目标

让用户打开网页后尽快开始说英语。

### 结构

1. 简短 Greeting：根据首次使用或回访显示自然问候。
2. 主操作 `Start Session`：首屏最突出。
3. `Continue Training`：存在 Active Task 或上次未完成训练时显示。
4. `Today's Focus`：使用自然语言描述今日建议，例如 “Practice expressing opinions more naturally”。
5. Active Tasks：最多展示 1-3 个简短任务。
6. Settings：低视觉权重入口。

### 状态

| 状态 | 行为 |
|---|---|
| first use | 只显示 Greeting、Start Session 和简短模式说明 |
| returning user | 显示 Continue Training 和最近关注方向 |
| active task | 显示任务标题、简短进度和 Continue |
| no active task | 显示 Start Session，不制造空洞的进度指标 |
| loading | 保持布局稳定，使用简单文本或轻量占位 |
| error | 显示可理解的重试信息，不显示内部错误堆栈 |

## 5. Start Session

### 设置项

| 设置 | 默认 | 说明 |
|---|---|---|
| Coach Mode | Foreign Friend | 影响 Agent 行为，不只是主题样式 |
| Session Duration | 15 分钟 | 提供 15 / 30 / 45 / 60 分钟和自定义 |
| Topic | General conversation | 可输入或选择轻量主题 |
| Language Mode | Auto | 只有后端支持时显示可用选项 |
| Start Session | - | 进入 Conversation |

### Coach Mode

#### Foreign Friend

像真实外国朋友聊天：尽可能不打断，普通 grammar mistake 不主动纠正，重点关注自然表达和沟通是否顺畅。只有沟通严重受影响时才介入，更多反馈集中在 Session Review。

#### Teacher

更系统地训练英语：允许更高介入概率，重复错误可以主动打断，更关注准确性、词汇、grammar 和 naturalness，并可进入 Targeted Practice。

#### Business Coach

面向商务环境：关注清晰度、专业表达、职场沟通和可能造成误解的表达，根据场景调整 vocabulary 与 expression。

Coach Mode 必须显示为清晰的行为选择，而不是仅用颜色或图标区分。用户选择 Mode 后，应能看到一句简短的行为描述。

## 6. Conversation

Conversation 是第一版最重要的页面，不采用普通 ChatGPT 式长列表作为主要构图。

### 页面结构

```text
┌──────────────────────────────────────────────┐
│ Coach identity     Topic             Time     │
├──────────────────────────────────────────────┤
│                                              │
│        当前 AI 状态 / 简短对话内容            │
│                                              │
│     最近一条用户表达      最近一条 Coach 回复   │
│                                              │
├──────────────────────────────────────────────┤
│      microphone / stop / retry               │
│      当前状态提示                            │
└──────────────────────────────────────────────┘
```

### 核心交互

1. 用户看到 Coach identity 和当前主题。
2. Microphone 是主要操作，拥有稳定、足够大的点击区域。
3. 用户说话、停止说话后，界面显示 processing，再展示 Coach 回复。
4. 回复出现后，用户可以立即继续说，不需要操作复杂控件。
5. 历史对话保留最近上下文即可，不要求首屏展示完整 transcript。
6. 剩余时间和 Session 状态始终可见，但不抢夺对话注意力。

当前后端主要依赖 Python 音频能力；Web UI 可以定义目标交互，但录音、STT 和实时音频需要后续 backend / browser 适配。

### 状态

| 状态 | UI 表现 |
|---|---|
| idle | Microphone 可用，提示 “Tap to speak” 或等价文本 |
| listening | Microphone 显示录音中，显示轻量波形或呼吸动画 |
| user speaking | 保持录音状态，不显示教学信息 |
| processing | 显示短暂处理中状态，不展示内部链路 |
| AI responding | 显示 Coach 回复和 speaking 状态 |
| intervention | 显示短暂、明确的反馈区域 |
| targeted practice | 切换到专项练习模式 |
| system error | 显示 “Something went wrong. Let’s try that again.” |
| session ending | 禁用重复输入，进入 Review 或结束确认 |

## 7. Agent Action 与 UI 映射

| Agent Action | 用户可见行为 | 是否打断 |
|---|---|---:|
| `continue` | 正常聊天，不显示教学 UI | 否 |
| `gentle_feedback` | 轻量反馈条或短暂 inline note，然后继续对话 | 否 |
| `interrupt` | 短、明确的 Intervention card，处理后立即回到对话 | 是 |
| `targeted_practice` | 显示 “Let's work on this for a moment.”，进入练习 | 是，短暂 |
| `task_follow_up` | 显示当前 Task context indicator，围绕任务继续 | 通常否 |
| `review_later` | 静默保留，Session Review 中呈现 | 否 |

`continue` 不应因为内部存在 Observation 或 Evidence 而展示分析提示。内部 Agent 复杂度只能影响行为，不应污染对话页面。

### Intervention 内容规则

- `gentle_feedback`：语气轻，避免红色错误标记和考试感。例如 “Small note — a more natural way to say that is…”。
- `interrupt`：只展示一个问题、一个建议和一个继续入口，不展示评分细节。
- `targeted_practice`：解释这是短暂专项训练，不暗示用户失败。
- `task_follow_up`：显示人能理解的长期目标，例如 “We’re practicing clearer workplace explanations.”。
- `review_later`：不显示 toast，不打断当前话题。

## 8. Targeted Practice

Targeted Practice 是一次训练活动，不是 Learning Task。它用于短暂离开 Conversation，解决一个具体问题，然后回到 Conversation。

### 四步流程

1. `correction`：展示更好的表达和极短解释。
2. `repetition`：邀请用户在相近语境再次表达。
3. `variation`：换一个场景，保持语言目标不变。
4. `free_use`：回到更自由的表达。

### UI 规则

- 顶部显示当前训练目标和 “Back to conversation”。
- 使用单一进度指示器，例如 `2 of 4`，不显示考试分数。
- 每一步只提供一个主要行动。
- 允许 `Skip` 或 `End practice`，用户始终可以结束。
- 练习结束后显示简短完成反馈并返回 Conversation。
- 失败不显示惩罚性文案；允许重复当前步骤或返回对话。
- Targeted Practice 完成不代表 Learning Task 完成。

当前 Agent Executor 的 targeted-practice handler 仍是安全占位；UI 可以定义目标页面，但不能假设当前 backend 已能自动启动全部流程。

## 9. Session Review

Session Review 不是考试报告，而是帮助用户理解下一步的对话总结。

### 内容结构

1. Session summary：一句自然语言总结今天的交流。
2. Things you did well：具体、鼓励性的表现。
3. Important corrections：少量高价值修正。
4. Natural expressions：值得记住的自然说法。
5. Communication issues：确实影响理解的问题。
6. Repeated patterns：重复出现但本次未打断的问题。
7. Recommended practice：下一次建议。
8. Active Task progress：已有任务的当前状态摘要。
9. Next session recommendation：下次继续什么。
10. Extension offer：存在高价值未完成任务时提供加时。

### Review 状态

| 状态 | UI |
|---|---|
| normal | 显示总结与少量重点 |
| no issues found | 显示 “You stayed clear and natural today.” 等正向总结 |
| issues found | 展示最多数项高价值问题 |
| recommended task | 显示推荐目标和确认操作 |
| active task exists | 显示 Continue task |
| extension available | 显示 Add 10 minutes / Finish session |

加时流程必须先询问用户：

> Would you like to practice this a little longer?

用户选择 `Add 10 minutes` 后才进入后续训练；选择 `Finish session` 或关闭时不得强制进入专项训练。

当前 Session Review 数据结构已有基础支持，但完整自动 Review 运行和持久化仍需后端能力，第一版 UI 应允许空数据状态。

## 10. Learning Task UI

Task 表示跨 Session 的有意义的长期训练目标，不展示内部错误计数作为主信息。

### 用户语言

优先显示：

- “Speak more naturally in everyday conversations.”
- “Explain ideas clearly in workplace conversations.”
- “Use a wider range of expressions when sharing opinions.”

避免显示：

- “Error count: 12”
- `historical_frequency`
- `PriorityResult.score`
- `Observation ID`

### Task 信息

- Goal
- Why this matters
- Progress 的自然语言摘要
- Recent evidence 的用户可理解表达
- Recommended next action

### 生命周期 UI

| 状态 | 用户看到什么 | 可用操作 |
|---|---|---|
| `proposed` | Coach 建议的目标和原因 | Accept / Not now |
| `accepted` | 已加入训练范围，但尚未开始 | Start when ready |
| `active` | 当前正在解决的目标 | Continue / Pause |
| `practicing` | 当前正在某次训练中 | Continue / End practice |
| `review` | 正在检查是否达到目标 | View review |
| `completed` | 已达到当前标准 | View history / Revisit later |
| `paused` | 暂停，不主动安排 | Resume |

用户拒绝 Proposed Task 后，不应在短期内重复弹出相同推荐。Task 状态修改必须经过既有 Task 生命周期接口；UI 不直接改变状态。

## 11. Long-term Goal UI

第一版可以是简单列表，不需要复杂图表。

```text
Long-term Goal
Speak naturally without translating in my head

Active Tasks
• Everyday natural expressions
• Expressing opinions
• Workplace communication

Next recommended step
Practice one short conversation
```

关系表达为：

```text
Long-term Goal → Learning Tasks → Sessions → Evidence → Progress
```

Evidence 在 UI 中应被翻译成可理解的近期观察，不直接显示内部字段。

## 12. 用户确认流程

以下操作必须有明确用户确认：

- 接受 Proposed Task
- 进入 Targeted Practice
- Session Review 加时
- 结束仍在进行的专项练习
- 暂停或取消一个 Active Task

确认应使用清晰的主次按钮，不使用模糊的自动跳转。用户拒绝、跳过或关闭都应是安全路径。

## 13. 空状态与错误状态

### 空状态

| 区域 | 文案方向 |
|---|---|
| Home 无任务 | “Start with a conversation. Your first focus will appear here.” |
| 无 Review 问题 | “Nothing urgent to work on today.” |
| 无历史 | “Your practice history will appear after a few sessions.” |
| 无推荐任务 | 不创建虚假推荐，显示继续聊天或下次再看 |

### 错误状态

- `system_error`：显示 “Something went wrong. Let’s try that again.”，绝不显示英语错误反馈。
- ASR uncertainty：显示 “I’m not sure I heard that. Could you say it again?”，或谨慎继续，不把它标成 English error。
- 录音权限错误：说明需要麦克风权限，并提供重试。
- 网络错误：保留当前 Session 状态，提供重试，不丢失已完成内容。
- Targeted Practice handler 不可用：安全回到 Conversation，说明当前练习暂时不可用，不伪造完成。

## 14. 视觉风格

方向：Modern AI product + language learning + warm conversational environment。

关键词：warm、calm、modern、immersive、minimal、human、premium but approachable。

避免：childish、过度游戏化、企业 Dashboard、考试软件、过多渐变、过多卡片、密集指标。

### 色彩方向

建议使用深色优先、低刺眼对比的中性背景，并以一个主要 accent 表达当前交互焦点。避免把每个 Agent 模块映射成不同颜色。

建议语义：

| 语义 | Dark | Light |
|---|---|---|
| background | 深炭灰或暖黑 | 柔和暖白或浅灰 |
| surface | 比背景略亮 | 比背景略深 |
| primary text | 柔和近白 | 深炭灰 |
| secondary text | 中性灰 | 深灰 |
| accent | 柔和暖色或低饱和青绿 | 同一 accent 的较深版本 |
| destructive | 低饱和红，仅用于真正错误 | 低饱和红 |

Accent 应主要用于 Microphone、Primary CTA、当前焦点和确认操作；不要使用大量彩色模块标签。

## 15. Typography 与间距

### Typography

- Heading：清晰、温和、有人的感觉，避免夸张 Display 字体。
- Body：优先可读性，16px 作为桌面正文基准。
- Conversation text：明显大于 metadata，建议 20-24px 桌面端、18-20px 移动端。
- User speech / Coach speech：通过位置、字重或轻微色差区分，不依赖颜色 alone。
- Button：短动词，清晰表达动作。
- Metadata：小而克制，不抢 Conversation 注意力。
- 不用超长标题、全大写或负 letter-spacing。

### 间距

使用稳定的 4px 基础尺度，主要间距优先使用 8 / 12 / 16 / 24 / 32 / 48px。Conversation 应有较大留白；设置、Task 和 Review 可更紧凑，但不得拥挤。

## 16. 组件风格

- Buttons：Primary CTA 明确；次要操作低对比；危险操作需要确认。
- Cards：只用于 Intervention、Task、Review item 等确实需要框定的内容；页面区域不要堆叠卡片。
- Conversation bubbles：少用传统聊天气泡，优先采用宽松的上下文块和说话者层级。
- Microphone button：首要操作，尺寸稳定，拥有可见 focus 和 listening 状态。
- Progress：使用步骤、语言摘要或细线进度，不突出分数。
- Task cards：展示 Goal、状态和下一步，不展示内部字段。
- Intervention card：短、单目标、可关闭或继续。
- Review sections：按优先级组织，不做密集仪表盘。
- Toast / Error：短文本、可读、可重试。
- Modal / Confirmation：仅用于明确需要确认的状态变化。

## 17. 动画原则

只使用服务于交流状态的轻量动画：

- Microphone listening：呼吸或轻微波形。
- AI thinking：低频、短暂的状态变化。
- Speaking state：轻量状态指示。
- Intervention transition：短暂淡入，不制造惊吓。
- Targeted Practice transition：明确但快速。

禁止大量粒子、持续移动背景、复杂 loading、游戏化庆祝和会分散注意力的动画。支持 `prefers-reduced-motion`，关闭非必要运动。

## 18. Responsive 原则

第一开发目标是 Desktop Web，同时支持 Tablet 和 Mobile。

### Desktop

- Conversation 内容居中且有舒适最大宽度。
- Microphone 与状态位于稳定、易达位置。
- 右侧或次级区域可展示 Topic、Time 和 Task context，但不压缩主要对话。

### Tablet

- 减少次要面板，保持 Microphone 和 Conversation 优先。
- Review、Task 内容改为单列或两列。

### Mobile

- Microphone 必须容易单手操作。
- 主要内容单列，避免频繁滚动。
- Session 状态固定但不遮挡对话。
- Intervention 和确认按钮宽度足够，长文本换行而不溢出。
- Targeted Practice 每一步只保留一个主操作。

## 19. Dark / Light Mode

Dark mode 是默认视觉方向，强调沉浸、安静和低刺眼感。Light mode 必须保留同一信息层级、accent 和状态语义，不应变成另一套产品。

两种模式都必须：

- 保证文本与控件对比度。
- 保留 listening、error、focus 等状态的可识别性。
- 避免纯黑背景和纯白大面积文字造成刺眼。
- 不依赖阴影或颜色 alone 表达结构。

## 20. Accessibility

- 所有功能可通过键盘访问。
- Microphone 必须有明确 accessible label、状态和操作反馈。
- 所有交互控件拥有可见 focus state。
- 文本和重要控件满足足够对比度。
- 正文和 Conversation text 保持可读字号。
- 不用颜色 alone 区分用户/Coach、错误/不确定性或 Task 状态。
- 录音、处理、回复和错误状态需要文本等价信息。
- 支持 `prefers-reduced-motion`。
- 键盘用户可以跳过重复导航并直接到达主要操作。

## 21. 当前可用能力与规划能力

### Available Now

- `TurnResult`、Observation、Evidence、Priority 和 Intervention 已有领域模型。
- `AgentDecision`、`ActionResult`、`AgentOrchestrator` 和 `ActionExecutor` 已定义最小决策与执行链。
- Coach Mode 已有 `foreign_friend`、`teacher`、`business_coach` 策略入口。
- `system_error` 和 ASR uncertainty 已有安全边界。
- LearningTask、TaskManager 和基础生命周期已存在。
- 现有 Python Session 有 TurnProcessor、LearningUpdateService、Router 和 TargetedPracticeManager。
- Session Review 已有基础数据结构和生成器。

### Planned / Needs Backend Support

- Web 浏览器录音、实时 STT、权限管理和流式回复。
- WebSocket 或等价实时通信。
- AgentDecision 与 Web Session 的正式 API 契约。
- Targeted Practice handler 的真实浏览器执行接口。
- Active Task 查询、用户确认和跨 Session Web 持久化。
- Session Review 的正式生成、持久化和展示接口。
- Task 推荐的接受、拒绝、暂停和恢复 API。
- Long-term Goal 的独立查询和进度聚合。
- Outcome Loop、自动 Evaluation 和完整 Task Progress。
- 多用户、数据库、账号和云部署。

当前不要为了填补这些缺口修改 backend。UI 规范可以先定义目标交互，但实现必须以真实接口能力为准。

## 22. UI 与 Agent 的边界

```text
Agent Core 决定：
Observation → Evidence → Priority → Intervention → AgentDecision

UI 负责：
展示状态 → 接收用户操作 → 请求执行 → 展示 ActionResult
```

UI 不重新判断优先级、是否打断、是否创建 Task 或是否进入专项训练。UI 也不直接修改 Memory、Performance、Task 或 Session；所有状态变化必须通过明确的应用接口。

## 23. 核心产品原则

1. Conversation comes first.
2. The AI should feel like a person, not a dashboard.
3. Do not interrupt unless the learning value justifies it.
4. Communication-impacting problems have higher priority than minor grammar issues.
5. Foreign Friend mode should feel like a real conversation.
6. Teacher mode should feel like coaching.
7. Business Coach mode should feel like professional communication training.
8. Targeted Practice should be short and purposeful.
9. Session Review should be more important than constant correction.
10. Learning Tasks should represent meaningful long-term improvement.
11. Internal Agent complexity should remain hidden from the user.
12. UI should support the Agent, not dictate its decision logic.

## 24. 当前不实现

本规范不包含：

- Web 前端代码
- React / Vue / Next / FastAPI 页面
- API、WebSocket 或录音前端
- 前端依赖和配置修改
- 真实 Targeted Practice 自动启动
- Outcome Loop
- 自动 Evaluation
- Goal Engine
- Semantic Task matching
- Embedding
- 多用户、数据库、账号、云部署
- TTS、语音重构、Prompt 重构
