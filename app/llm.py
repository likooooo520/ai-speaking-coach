import json
import re

from openai import OpenAI

from app.config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_MODEL,
)

from app.coach import CoachDecision
from app.memory import ErrorMemory
from app.naturalness import NaturalnessMemory
from app.performance import PerformanceTracker


_SESSION_CONTEXT_UNSET = object()


class DeepSeekCoach:

    def __init__(self):

        self.client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
            timeout=30.0,
            max_retries=0
        )

        # 当前 Session 对话历史
        self.conversation_history = []

        # 当前 Session 内自然表达的出现次数。
        self.naturalness_observations = {}

        # 长期错误记忆
        self.error_memory = ErrorMemory()

        # 长期自然表达记忆
        self.naturalness_memory = (
            NaturalnessMemory()
        )

        # 表现与难度
        self.performance_tracker = (
            PerformanceTracker()
        )

        # 当前 Session 上下文
        self.session_context = {
            "duration_minutes": 45,
            "phase": "warmup",
            "topic": "general conversation",
            "language_mode": "auto",
            "coach_mode": "automatic",
            "feedback_intensity": "light",
            "session_difficulty": "B2",
            "professional_context": "",
            "targeted_practice_context": "",
            "coaching_context": "",
        }

    # ========================================
    # Session Context
    # ========================================

    def set_session_context(
            self,
            duration_minutes=_SESSION_CONTEXT_UNSET,
            phase=None,
            topic=None,
            language_mode=None,
            coach_mode=None,
            feedback_intensity=None,
            session_difficulty=None,
            professional_context=None,
            targeted_practice_context=None,
            coaching_context=None,
    ):
        if targeted_practice_context is not None:
            self.session_context[
                "targeted_practice_context"
            ] = targeted_practice_context

        if coaching_context is not None:
            self.session_context["coaching_context"] = coaching_context

        if duration_minutes is not _SESSION_CONTEXT_UNSET:

            self.session_context[
                "duration_minutes"
            ] = duration_minutes

        if phase is not None:

            self.session_context[
                "phase"
            ] = phase

        if topic is not None:

            self.session_context[
                "topic"
            ] = topic

        if language_mode is not None:

            self.session_context[
                "language_mode"
            ] = language_mode

        if coach_mode is not None:

            self.session_context[
                "coach_mode"
            ] = coach_mode

        if feedback_intensity is not None:

            self.session_context[
                "feedback_intensity"
            ] = feedback_intensity

        if session_difficulty is not None:

            self.session_context[
                "session_difficulty"
            ] = session_difficulty

        if professional_context is not None:

            self.session_context[
                "professional_context"
            ] = professional_context

    # ========================================
    # System Prompt
    # ========================================

    def _system_prompt(self):

        current_difficulty = (
            self.performance_tracker
            .get_current_difficulty()
        )

        phase = self.session_context[
            "phase"
        ]

        topic = self.session_context[
            "topic"
        ]

        language_mode = self.session_context[
            "language_mode"
        ]

        coach_mode = self.session_context[
            "coach_mode"
        ]

        feedback_intensity = self.session_context.get(
            "feedback_intensity", "light"
        )

        prompt = """
You are an AI English Speaking Coach.

The learner is training spoken English through a structured
adaptive training session.

CURRENT LEARNER LEVEL
---------------------
Target starting level: B2

Current adaptive difficulty:
DIFFICULTY_PLACEHOLDER

CURRENT SESSION
---------------
Current phase:
PHASE_PLACEHOLDER

Current topic:
TOPIC_PLACEHOLDER

Language mode:
LANGUAGE_MODE_PLACEHOLDER

Coach mode:
COACH_MODE_PLACEHOLDER

Feedback intensity:
FEEDBACK_INTENSITY_PLACEHOLDER

YOUR TWO ROLES
--------------
You are both:

1. A natural English conversation partner.
2. An English speaking coach.

The learner should speak more than the coach.

SESSION PHASE BEHAVIOR
----------------------

WARMUP:
- Keep the conversation easy and relaxed.
- Help the learner switch into English mode.
- Do not over-correct.
- Ask simple but natural questions.

MAIN_CONVERSATION:
- Maintain natural B2-level conversation.
- Ask follow-up questions.
- Encourage explanations, examples, and opinions.
- The learner should do most of the speaking.

DEEP_DISCUSSION:
- Explore opinions, reasons, consequences,
  comparisons, and alternative perspectives.
- Encourage nuanced B2+/C1-style speaking.

CHALLENGE:
- Push the learner slightly beyond comfort.
- Ask more demanding questions.
- Encourage longer answers.
- Encourage precise vocabulary.

TARGETED_PRACTICE:
- Focus on recurring problems that are relevant
  to the learner's CURRENT speech.
- Practice repeated errors.
- Practice useful natural alternatives.
- Ask the learner to rephrase or try again.
- Do not randomly bring up unrelated historical errors.

TARGETED PRACTICE ENGINE
------------------------
When targeted practice is active, the learner is practicing
one specific issue.

The targeted practice has four possible steps:

1. correction
   Briefly explain the issue and ask the learner to repeat
   the corrected expression.

2. repetition
   Ask the learner to use the corrected expression again.

3. variation
   Give a slightly different situation and ask the learner
   to use the same language pattern.

4. free_use
   Let the learner use the expression naturally in conversation.

Do not simply continue the original conversation topic.

The goal is to actively practice the target language.

REVIEW:
- Focus on the most important improvements from
  this session.
- Ask the learner to reuse useful expressions.
- Keep the review practical.

LANGUAGE MODE
-------------
If language mode is "auto":
- primarily use English
- use brief support only when necessary

If language mode is "english_only":
- use only English

COACH MODE
----------
If coach mode is "foreign_friend": act as an English-speaking friend.
Keep the conversation natural. Do not proactively correct, explain grammar,
or turn replies into lessons unless the learner's meaning is genuinely unclear.

If coach mode is "teacher": be a supportive coach during natural conversation.
Offer at most one light, useful improvement when it fits naturally.

If coach mode is "business_coach": use a professional, realistic tone for
work, interview, meeting, client, or formal social situations. Do not use
childlike teaching language or interrupt unnecessarily.

Do not correct every mistake in any mode. Correct only important, repeated,
or clearly unnatural mistakes.

FEEDBACK INTENSITY
------------------
Respect the configured feedback intensity: "light" means only occasional,
brief feedback; "normal" permits regular concise feedback; "strong" permits
more active feedback while keeping the conversation natural.

NATURALNESS VS ERROR
--------------------
This distinction is extremely important.

A sentence can be grammatically acceptable but have a
more natural alternative.

For example:

"I like many foods."

This can be acceptable English in some contexts.

Do NOT automatically label it as an error.

If a more conversational expression would be useful,
classify it as a NATURALNESS suggestion instead.

For example:

"I like all kinds of food."

"I am into all kinds of food."

However:

"I like many food."

is a genuine language problem in this context.

It can be corrected to:

"I like many kinds of food."

Do not treat every possible improvement as an error.

NATURALNESS FEEDBACK
--------------------
Do not generate naturalness feedback after every sentence.

Use it when:
- the learner repeatedly uses the same expression
- an expression sounds noticeably textbook-like
- an expression sounds translated
- a more conversational alternative is clearly useful

If the learner uses "I think" once:
do NOT necessarily comment.

If the learner repeatedly uses "I think" across the session:
a naturalness suggestion becomes more useful.

ERROR MEMORY
------------
Previous learner errors may be provided.

Repeated errors have higher priority.

Do not force an old error into an unrelated conversation.

ASR
---
Whisper can make recognition mistakes.

Distinguish likely ASR errors from actual English mistakes.

Do not blame the learner for likely Whisper mistakes.

PERFORMANCE
-----------
Evaluate:

fluency
grammar
vocabulary
naturalness
overall

Use a 0-10 scale.

strong:
overall >= 8

weak:
overall < 6

normal:
otherwise

Also provide:

suggested_action:
increase
maintain
decrease

Python controls actual difficulty changes using
consecutive performance.

OUTPUT
------
Return ONLY one JSON object.

{
    "reply": "natural conversational response",

    "correction": {
        "needed": false,
        "original": null,
        "better": null,
        "explanation": null
    },

    "asr_uncertainty": [],

    "naturalness": {
        "detected": false,
        "original": null,
        "alternatives": [],
        "explanation": null,
        "category": "expression"
    },

    "performance": {
        "fluency": 7.0,
        "grammar": 7.0,
        "vocabulary": 7.0,
        "naturalness": 7.0,
        "overall": 7.0,
        "band": "normal",
        "suggested_action": "maintain"
    },

    "conversation_topic": "current topic",

    "difficulty": "B2",

    "next_action": "continue_conversation"
}

ASR UNCERTAINTY MUST BE AN ARRAY OF OBJECTS.

If none:

[]

If present:

[
    {
        "heard": "something",
        "possible": "something else",
        "confidence": "medium"
    }
]

Return JSON only.
Do not use Markdown.
"""

        prompt = prompt.replace(
            "DIFFICULTY_PLACEHOLDER",
            current_difficulty
        )

        prompt = prompt.replace(
            "PHASE_PLACEHOLDER",
            phase
        )

        prompt = prompt.replace(
            "TOPIC_PLACEHOLDER",
            topic
        )

        prompt = prompt.replace(
            "LANGUAGE_MODE_PLACEHOLDER",
            language_mode
        )

        prompt = prompt.replace(
            "COACH_MODE_PLACEHOLDER",
            coach_mode
        )

        prompt = prompt.replace(
            "FEEDBACK_INTENSITY_PLACEHOLDER",
            feedback_intensity
        )

        return prompt

    # ========================================
    # Build Messages
    # ========================================

    def _build_messages(
        self,
        user_text
    ):

        error_context = (
            self.error_memory
            .get_llm_context(
                limit=5
            )
        )

        naturalness_context = (
            self.naturalness_memory
            .get_llm_context(
                limit=5
            )
        )

        difficulty = (
            self.performance_tracker
            .get_current_difficulty()
        )

        duration_label = (
            "No fixed duration"
            if self.session_context["duration_minutes"] is None
            else f"{self.session_context['duration_minutes']} minutes"
        )
        session_context = (
            "SESSION CONTEXT:\n"
            f"Duration: "
            f"{duration_label}\n"
            f"Phase: "
            f"{self.session_context['phase']}\n"
            f"Topic: "
            f"{self.session_context['topic']}\n"
            f"Language mode: "
            f"{self.session_context['language_mode']}\n"
            f"Coach mode: "
            f"{self.session_context['coach_mode']}\n"
            f"Difficulty: "
            f"{difficulty}"
            f"\n"
            f"Targeted practice context: "
            f"{self.session_context['targeted_practice_context']}"
        )

        messages = [
            {
                "role": "system",
                "content": self._system_prompt()
            },
            {
                "role": "system",
                "content": session_context
            },
            {
                "role": "system",
                "content": (
                    "LONG-TERM ERROR MEMORY:\n\n"
                    + error_context
                )
            },
            {
                "role": "system",
                "content": (
                    "LONG-TERM NATURALNESS MEMORY:\n\n"
                    + naturalness_context
                )
            }
        ]

        messages.extend(
            self.conversation_history
        )

        messages.append(
            {
                "role": "user",
                "content": user_text
            }
        )

        return messages

    # ========================================
    # DeepSeek Request
    # ========================================

    def _request_deepseek(
        self,
        messages,
        response_format=None,
        attempt=1,
    ):

        try:

            request = {
                "model": DEEPSEEK_MODEL,
                "messages": messages,
                "stream": False,
                "extra_body": {
                    "thinking": {
                        "type": "disabled"
                    }
                },
            }
            if response_format is not None:
                request["response_format"] = response_format

            response = self.client.chat.completions.create(**request)

            choice = response.choices[0]

            content = (
                choice.message.content
            )

            finish_reason = getattr(
                choice,
                "finish_reason",
                None
            )

            if not str(content or "").strip():
                self._deepseek_response_status = "EMPTY_CONTENT"
                self._log_empty_deepseek_response(
                    response,
                    choice,
                    attempt=attempt,
                )
            else:
                self._deepseek_response_status = "OK"

            return content, finish_reason

        except Exception as e:
            self._deepseek_response_status = "ERROR"
            self._log_deepseek_exception(e)

            return None, "error"

    def _log_deepseek_exception(
        self,
        error
    ):
        """输出不含请求内容或凭据的 SDK 异常诊断信息。"""
        response = getattr(error, "response", None)
        headers = getattr(response, "headers", None)
        status_code = (
            getattr(error, "status_code", None)
            or getattr(response, "status_code", None)
        )
        request_id = (
            getattr(error, "request_id", None)
            or getattr(error, "_request_id", None)
        )

        if request_id is None and headers is not None:
            request_id = (
                headers.get("x-request-id")
                or headers.get("request-id")
            )

        message = str(error)
        if DEEPSEEK_API_KEY:
            message = message.replace(
                DEEPSEEK_API_KEY,
                "[REDACTED]"
            )

        print()
        print("ERROR: DeepSeek request failed")
        print(
            "DeepSeek exception diagnostic: "
            + json.dumps(
                {
                    "exception_type": type(error).__name__,
                    "http_status": status_code,
                    "error_message": message,
                    "request_id": request_id,
                },
                ensure_ascii=False,
                default=str,
            )
        )
        print()

    def _log_empty_deepseek_response(
        self,
        response,
        choice,
        attempt=1,
    ):
        """仅记录空内容响应的最小安全诊断字段。"""
        response_dump = response.model_dump()
        message = choice.message
        content = getattr(message, "content", None)
        reasoning_content = getattr(
            message,
            "reasoning_content",
            None
        )
        tool_calls = getattr(message, "tool_calls", None)

        diagnostic = {
            "attempt": attempt,
            "response_model": getattr(response, "model", None),
            "choices_count": len(getattr(response, "choices", [])),
            "finish_reason": getattr(
                choice,
                "finish_reason",
                None
            ),
            "content_is_empty": not bool(
                str(content or "").strip()
            ),
            "reasoning_content_present": (
                reasoning_content is not None
            ),
            "tool_calls_present": tool_calls is not None,
            "total_tokens": (response_dump.get("usage") or {}).get("total_tokens"),
            "request_id": (
                getattr(response, "_request_id", None)
                or getattr(response, "request_id", None)
            ),
        }

        print(
            "DeepSeek empty response diagnostic: "
            + json.dumps(
                diagnostic,
                ensure_ascii=False,
                default=str,
            )
        )

    # ========================================
    # Main Chat
    # ========================================

    def chat(
        self,
        user_text
    ):

        messages = self._build_messages(
            user_text
        )

        max_attempts = 2

        raw_response = None

        finish_reason = None

        for attempt in range(
            1,
            max_attempts + 1
        ):

            print()

            print(
                f"DeepSeek request "
                f"{attempt}/{max_attempts}..."
            )

            raw_response, finish_reason = (
                self._request_deepseek(messages, response_format={"type": "json_object"})
            )

            if (
                raw_response is not None
                and str(raw_response).strip()
            ):

                break

            print(
                "DeepSeek did not return "
                "a usable response."
            )

            if attempt < max_attempts:

                print(
                    "Retrying..."
                )

        if (
                raw_response is None
                or not str(raw_response).strip()
        ):
            print()
            print(
                "ERROR: DeepSeek is temporarily unavailable."
            )

            print(
                "This turn will not affect your "
                "learning progress."
            )

            print()

            return CoachDecision(
                reply=(
                    "Sorry, I couldn't reach "
                    "the coach just now. "
                    "Please try that again."
                ),
                system_error=True,
                next_action="ask_clarification"
            )

        decision = self._parse_response(
            raw_response
        )

        # 解析失败属于无效 Coach Turn，不得进入历史或学习数据。
        if decision.system_error:
            return decision

        self._apply_feedback_rules(
            user_text,
            decision
        )

        # 保存 Session 对话历史
        self.conversation_history.append(
            {
                "role": "user",
                "content": user_text
            }
        )

        self.conversation_history.append(
            {
                "role": "assistant",
                "content": decision.reply
            }
        )

        return decision


    # ========================================
    # Feedback Rules
    # ========================================

    def _apply_feedback_rules(
        self,
        user_text,
        decision,
        *,
        require_naturalness_repetition=True,
    ):
        """在保存学习数据前保护 Error/Naturalness 边界。"""

        text = (
            user_text or ""
        ).strip()

        # ASR 不确定时，不把模型猜测直接当成英语错误。
        if decision.asr_uncertainty:
            decision.correction = decision.correction.model_copy(
                update={
                    "needed": False,
                    "original": None,
                    "better": None,
                    "explanation": None
                }
            )
            return

        # 这是当前语境下的明确可判定错误。
        if re.search(r"\bmany\s+food\b", text, re.IGNORECASE):
            decision.correction.needed = True
            decision.correction.original = "many food"
            decision.correction.better = "many kinds of food"
            if not decision.correction.explanation:
                decision.correction.explanation = (
                    "Food is uncountable in this context."
                )

        # many foods 是可接受表达，不应被默认纠正。
        elif re.search(r"\bmany\s+foods\b", text, re.IGNORECASE):
            decision.correction = decision.correction.model_copy(
                update={
                    "needed": False,
                    "original": None,
                    "better": None,
                    "explanation": None
                }
            )

        # 自然度反馈必须建立在当前 Session 的重复使用上。
        naturalness = decision.naturalness
        if naturalness.detected and naturalness.original:
            key = naturalness.original.strip().lower()
            if key and key in text.lower():
                count = self.naturalness_observations.get(key, 0) + 1
                self.naturalness_observations[key] = count
                if require_naturalness_repetition and count < 3:
                    decision.naturalness = naturalness.model_copy(
                        update={
                            "detected": False,
                            "original": None,
                            "alternatives": [],
                            "explanation": None
                        }
                    )

    # ========================================
    # Normalize ASR
    # ========================================

    def _normalize_asr(
        self,
        value
    ):

        if not value:
            return []

        result = []

        for item in value:

            if isinstance(
                item,
                dict
            ):

                heard = item.get(
                    "heard"
                )

                if not heard:
                    continue

                result.append(
                    {
                        "heard": str(
                            heard
                        ),
                        "possible": item.get(
                            "possible"
                        ),
                        "confidence": item.get(
                            "confidence",
                            "low"
                        )
                    }
                )

            elif isinstance(
                item,
                str
            ):

                result.append(
                    {
                        "heard": item,
                        "possible": None,
                        "confidence": "low"
                    }
                )

        return result

    # ========================================
    # Parse Response
    # ========================================

    def _parse_response(
        self,
        raw_response
    ):

        if (
            raw_response is None
            or not str(raw_response).strip()
        ):

            return CoachDecision(
                reply=(
                    "Could you say that again?"
                ),
                next_action="ask_clarification"
            )

        raw_response = str(
            raw_response
        ).strip()

        if raw_response.startswith(
            "```"
        ):

            lines = (
                raw_response
                .splitlines()
            )

            if (
                lines
                and lines[0].strip()
                in (
                    "```",
                    "```json"
                )
            ):

                lines = lines[1:]

            if (
                lines
                and lines[-1].strip()
                == "```"
            ):

                lines = lines[:-1]

            raw_response = (
                "\n".join(lines)
                .strip()
            )

        try:

            data = json.loads(
                raw_response
            )

        except json.JSONDecodeError:

            print()
            print(
                "Coach JSON parse failed"
            )

            print(
                "Raw response:"
            )

            print(
                raw_response
            )

            print()

            return CoachDecision(
                reply=raw_response,
                system_error=True,
                next_action=(
                    "ask_clarification"
                )
            )

        if not isinstance(data, dict):
            print()
            print("ERROR: Coach response must be a JSON object")
            print()
            return CoachDecision(
                reply="Sorry, the coach returned an invalid response.",
                system_error=True,
                next_action="ask_clarification"
            )

        # ====================================
        # Normalize fields
        # ====================================

        data[
            "asr_uncertainty"
        ] = self._normalize_asr(
            data.get(
                "asr_uncertainty",
                []
            )
        )

        if "naturalness" not in data:

            data["naturalness"] = {
                "detected": False,
                "original": None,
                "alternatives": [],
                "explanation": None,
                "category": "expression"
            }

        if "performance" not in data:

            data["performance"] = {
                "fluency": 7.0,
                "grammar": 7.0,
                "vocabulary": 7.0,
                "naturalness": 7.0,
                "overall": 7.0,
                "band": "normal",
                "suggested_action": "maintain"
            }

        try:

            return (
                CoachDecision
                .model_validate(
                    data
                )
            )

        except Exception as e:

            print()
            print(
                "ERROR: Coach data validation failed"
            )

            print(
                f"Error: {e}"
            )

            print()

            return CoachDecision(
                reply=str(
                    data.get(
                        "reply",
                        "Could you say that again?"
                    )
                ),
                system_error=True,
                next_action=(
                    "ask_clarification"
                )
            )


class ConversationCoach(DeepSeekCoach):
    """面向 Web 连续对话的普通文本教练，不依赖 JSON 输出。"""

    def _conversation_prompt(self):
        topic = self.session_context["topic"]
        coach_mode = self.session_context.get("coach_mode", "automatic")
        difficulty = self.session_context.get("session_difficulty", "B2")
        professional_context = self.session_context.get("professional_context") or ""
        coaching_context = self.session_context.get("coaching_context") or ""
        teaching = (
            f"\n\nTeaching context:\n{coaching_context}"
            if coach_mode in {"teacher", "automatic"} and coaching_context else ""
        )
        mode_instruction = {
            "foreign_friend": """
You are the learner's English-speaking friend, not their teacher. Respond to
meaning naturally and do not volunteer corrections, vocabulary suggestions,
naturalness advice, or practice. Clarify briefly only when meaning is genuinely
unclear. A reply may be a comment, a shared view, or a question; do not force a question every turn or repeat stock follow-ups.""",
            "teacher": """
You are a supportive English coach in a natural conversation. Conversation comes
first. When it genuinely helps, offer at most one short, practical improvement;
otherwise just continue the conversation. Do not turn every reply into a lesson.""",
            "business_coach": """
You are a professional conversation partner, not a business-English lecturer.
Use precise, professional English and sustain one realistic workplace context.
Do not volunteer grammar lessons or casual slang. Continue from the learner's
actual answer instead of switching to a scripted question list.""",
        }.get(coach_mode, "You are a natural English conversation partner.")
        professional = (
            f"\nProfessional context: {professional_context}" if professional_context else ""
        )
        return f"""
You are having a live English conversation.

Use English by default. Keep vocabulary, sentence complexity, and topic depth
appropriate for the Session target level: {difficulty}. Respond like a real
person: acknowledge the learner's meaning, feeling, experience, or opinion, then
continue naturally when there is something useful to add.

Keep each reply to one to three short sentences. Do not correct every mistake,
do not interrupt the learner for minor issues, and do not switch topics mechanically.
Keep the tone varied and conversational. Avoid repeatedly opening with the same praise
or asking more than one main question. If the learner asks for clarification, explain
briefly with one simple example. If the learner is ending the conversation, close warmly
without asking a new question.

Current conversation topic: {topic}
Mode: {coach_mode}
{mode_instruction}
{professional}
{teaching}

OUTPUT
------
Return one JSON object only. The learner sees only "reply"; all other fields are
private learning signals. Do not mention those fields in the reply.

{{
  "reply": "natural conversational response",
  "correction": {{
    "needed": false,
    "original": null,
    "better": null,
    "explanation": null
  }},
  "naturalness": {{
    "detected": false,
    "original": null,
    "alternatives": [],
    "explanation": null,
    "category": "expression"
  }},
  "asr_uncertainty": []
}}

Only report a correction or naturalness signal when it is clear, useful, and
grounded in the learner's current words. Do not treat likely ASR uncertainty as
an English mistake. In foreign_friend mode, never surface a signal as teaching in
the reply; it is only available for the post-session review.
""".strip()

    def _build_conversation_messages(self, user_text):
        return [
            {"role": "system", "content": self._conversation_prompt()},
            *self.conversation_history,
            {"role": "user", "content": user_text},
        ]

    def chat(self, user_text):
        messages = self._build_conversation_messages(user_text)
        raw_response = None

        for attempt in range(1, 3):
            print()
            print(f"DeepSeek conversation request {attempt}/2...")
            raw_response, _ = self._request_deepseek(
                messages, response_format={"type": "json_object"}, attempt=attempt
            )
            if raw_response is not None and str(raw_response).strip():
                break
            if getattr(self, "_deepseek_response_status", "ERROR") != "EMPTY_CONTENT":
                break
            if attempt == 1:
                print("Retrying once...")

        if raw_response is None or not str(raw_response).strip():
            print("ERROR: DeepSeek conversation is temporarily unavailable.")
            return CoachDecision(
                reply="I missed that. Could you say it again?",
                system_error=True,
                next_action="ask_clarification",
            )

        decision = self._parse_response(raw_response)
        if decision.system_error:
            return decision

        self._apply_feedback_rules(
            user_text,
            decision,
            require_naturalness_repetition=(
                self.session_context.get("coach_mode") != "teacher"
            ),
        )
        self.conversation_history.extend([
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": decision.reply},
        ])
        return decision
