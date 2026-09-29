# AI Speaking Coach

通过自然对话练习英语表达的自适应口语教练。

设计目标不是「聊得多」，而是**在合适的时候给出合适的干预**：既不频繁纠错打断表达，也不让 ASR 误识别污染长期学习记录。

## 核心设计

### 1. 可解释的 Agent 决策链

每轮对话走一条确定性、可测试、可回放的链路，而不是把 LLM 包一层：

```text
TurnContext → TurnProcessor → Coach → TurnResult
            → ObservationBuilder → Observation + Evidence
            → PriorityEngine → PriorityResult
            → InterventionPolicy → InterventionDecision
            → Task candidate / Action hint / Continue
            → Session Review candidate
```

- **Observation** 只保存本轮事实快照；**Evidence** 记录「这个事实为什么具有学习意义」（历史匹配、频率、用户显式请求、ASR 不确定性、打断成本）。两者都不写 Memory，保持无副作用与可测试。
- **PriorityEngine** 用确定性权重与集中定义的阈值选出当前最值得关注的信号，不把优先级判断交给 LLM——结果可复现、可回放。
- **InterventionPolicy** 输出 5 种动作：`continue` / `light_feedback` / `interrupt` / `targeted_practice` / `review_later`，在打断成本与学习收益之间权衡。

### 2. ASR 不确定性守门

语音识别不可靠时，识别内容**不允许**写入 Error Memory。否则长期学习记录会被污染，后续训练会针对「用户根本没犯的错」——这是本项目与一般口语机器人的关键差异。

### 3. 长期记忆与任务生命周期

- 三类长期状态：**Error Memory** / **Naturalness Memory** / **Performance**，仅在规则验证后写入。
- Task 生命周期 `proposed → active` 由 `TaskManager` 作为**唯一写入边界**；`TargetedPractice` 只执行训练，不拥有或完成任务。
- Session 结束时由 `SessionReviewGenerator` 汇总高价值观察、重复问题、沟通问题与推荐任务。

## 技术栈

| 层 | 选型 |
| --- | --- |
| LLM | DeepSeek（OpenAI 兼容接口） |
| ASR | faster-whisper（`small`，CUDA + float16） |
| TTS | Edge TTS |
| 领域建模 | Pydantic |
| Web 前端 | 原生 JavaScript（无框架） |
| 测试 | unittest，190+ 条用例 |

## 目录结构

```text
app/
├── domain/          纯领域模型：observation / evidence / priority / intervention / action / learning / task / turn
├── application/     编排与服务：agent_orchestrator / priority_engine / intervention_policy / session_review / task_manager …
├── infrastructure/  持久化：task_repository
├── coach.py         LLM 教练决策
├── stt.py           faster-whisper 封装
├── memory.py        长期记忆读写
└── web.py           Web UI 服务
web/                 原生 JS 前端（index.html + assets/）
docs/                AGENT_ARCHITECTURE / AGENT_SPEC / LEARNING_TASKS / ROADMAP / WEB_UI_SPEC
tests/               单元测试
```

## 快速开始

依赖 Python 3.11+，可选 NVIDIA GPU（faster-whisper 的 CUDA 推理）。

```bash
# 1. 配置密钥
cp .env.example .env      # 填入 DEEPSEEK_API_KEY

# 2. 安装依赖
pip install faster-whisper edge-tts pydantic python-dotenv

# 3. 启动 Web UI
python -m app.web         # http://127.0.0.1:8000

# 或启动 CLI
python app/main.py
```

音频格式转换需要本机有 `ffmpeg`。

## 测试

```bash
python -m pip install pytest pytest-cov
python -m pytest tests -q --cov=app --cov-report=term
```

当前 193 个用例全部通过，核心决策层覆盖率为 95%。

## 评测

`evals/` 是决策链的**规格符合性评测**：43 条标注场景 + 8 条直接从规格文档提取的不变量
（ASR 不确定不介入、未请求不建任务、单次错误不高优先级等）。

```bash
python -m evals.run_decision_eval
```

首次运行定位到 3 处实现与规格的偏差——浮点误差导致优先级阈值边界失效、
`recently_practiced` 在 Priority 与 Intervention 两层数据源不一致导致守卫失效、
无效 Observation 仍产出优先级。修复后 43/43 场景与 8/8 不变量全部通过。
方法与缺陷记录见 [`evals/README.md`](evals/README.md)。

## 范围说明

本项目按 Task 粒度迭代，已完成 Agent Core、长期记忆、Targeted Practice、Session Review 与 Web UI 的**最小决策闭环**。

仍在路线图中、尚未实现的能力：Outcome Loop（动作效果评估与反馈闭环）、Learning Goal Engine、自动评测、复杂 embedding / 语义检索、Topic Discovery、多用户与产品化。详见 [`docs/AGENT_ARCHITECTURE.md`](docs/AGENT_ARCHITECTURE.md) 与 [`docs/ROADMAP.md`](docs/ROADMAP.md)。

## 文档

- [`docs/AGENT_ARCHITECTURE.md`](docs/AGENT_ARCHITECTURE.md) — 决策链分层与依赖边界
- [`docs/AGENT_SPEC.md`](docs/AGENT_SPEC.md) — Observation / Evidence / Priority 契约
- [`docs/LEARNING_TASKS.md`](docs/LEARNING_TASKS.md) — 学习任务定义
- [`docs/WEB_UI_SPEC.md`](docs/WEB_UI_SPEC.md) — Web UI 交互规范
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — 路线图
