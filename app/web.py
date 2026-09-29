"""AI Speaking Coach 的轻量 Web 适配层。"""

import json
import os
from email.parser import BytesParser
from email.policy import default
import threading
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.application.agent_orchestrator import AgentOrchestrator
from app.application.audio_converter import AudioConversionError, AudioConverter, FfmpegUnavailableError
from app.application.turn_processor import TurnProcessor
from app.application.learning_analysis_service import LearningAnalysisService
from app.application.edge_tts_provider import EdgeTTSProvider
from app.application.tts_provider import TTSProvider
from app.application.action_executor import ActionExecutor
from app.application.targeted_practice_service import TargetedPracticeService
from app.expression_library import ExpressionLibrary
from app.llm import ConversationCoach
from app.domain.turn import TurnContext

WEB_ROOT = Path(__file__).resolve().parent.parent / "web"
AUDIO_ROOT = Path(__file__).resolve().parent.parent / "data" / "web_audio"
MAX_AUDIO_BYTES = 10 * 1024 * 1024
ALLOWED_AUDIO_TYPES = {"audio/webm", "audio/ogg", "audio/wav", "audio/x-wav", "audio/mpeg"}

_shared_stt = None
_stt_init_lock = threading.Lock()
_stt_transcribe_lock = threading.Lock()
TTS_PROVIDER: TTSProvider | None = EdgeTTSProvider()
SUPPORTED_TTS_VOICES = {getattr(TTS_PROVIDER, "voice", "en-US-AriaNeural"), "en-US-AriaNeural"}
SUPPORTED_SPEAKING_RATES = {0.7, 0.8, 0.9, 1.0, 1.1, 1.2}


def edge_tts_rate(speaking_rate: Any) -> str:
    """将前端倍速转换为 Edge TTS 所需的百分比速率。"""
    try:
        rate = round(float(speaking_rate), 1)
    except (TypeError, ValueError):
        rate = 1.0
    if rate not in SUPPORTED_SPEAKING_RATES:
        rate = 1.0
    return f"{round((rate - 1) * 100):+d}%"


def _speech_to_text_factory():
    from app.stt import SpeechToText
    return SpeechToText


def _get_shared_stt():
    """懒加载并缓存 Web 服务级 SpeechToText 实例。"""
    global _shared_stt
    if _shared_stt is None:
        with _stt_init_lock:
            if _shared_stt is None:
                # 初始化失败时不写入全局缓存，后续请求可以重试。
                _shared_stt = _speech_to_text_factory()()
    return _shared_stt


def transcribe_uploaded_audio(filename, stt_factory=None, converter=None):
    """转换上传音频后调用现有 SpeechToText，并始终清理临时 WAV。"""
    converter = converter or AudioConverter()
    fd, temp_name = tempfile.mkstemp(prefix="speaking-coach-", suffix=".wav",
                                     dir=Path(filename).parent)
    os.close(fd)
    temp_wav = Path(temp_name)
    try:
        converter.convert_to_wav(filename, temp_wav)
        if stt_factory is None:
            stt = _get_shared_stt()
            with _stt_transcribe_lock:
                text = stt.transcribe(str(temp_wav))
        else:
            text = stt_factory().transcribe(str(temp_wav))
        if not text or not text.strip():
            raise ValueError("transcription is empty")
        return text.strip()
    finally:
        temp_wav.unlink(missing_ok=True)


class WebSession:
    def __init__(self, payload: dict[str, Any]):
        self.session_id = str(uuid4())
        requested_duration = payload.get("duration", 45)
        self.duration = None if requested_duration is None else int(requested_duration)
        self.topic = payload.get("topic") or None
        self.mode = payload.get("mode") or "foreign_friend"
        self.difficulty = payload.get("difficulty") or "B2"
        self.english_only = bool(payload.get("english_only", False))
        self.feedback_intensity = payload.get("feedback_intensity") or "light"
        requested_voice = payload.get("voice_name") or getattr(TTS_PROVIDER, "voice", "en-US-AriaNeural")
        self.voice_name = requested_voice if requested_voice in SUPPORTED_TTS_VOICES else "en-US-AriaNeural"
        try:
            speaking_rate = round(float(payload.get("speaking_rate", 1.0)), 1)
        except (TypeError, ValueError):
            speaking_rate = 1.0
        self.speaking_rate = speaking_rate if speaking_rate in SUPPORTED_SPEAKING_RATES else 1.0
        self.session_voice_rate = max(0.7, min(1.2, self.speaking_rate))
        self.tts_rate = edge_tts_rate(self.session_voice_rate)
        self.auto_tts = bool(payload.get("auto_tts", True))
        try:
            self.volume = min(1.0, max(0.0, float(payload.get("volume", 1.0))))
        except (TypeError, ValueError):
            self.volume = 1.0
        self.turns: list[dict[str, Any]] = []
        self.learning_analysis: list[dict[str, Any]] = []
        self.coaching_context: list[dict[str, Any]] = []
        self._coaching_context_counter = 0
        self._lock = threading.RLock()
        self._speak_lock = threading.Lock()
        self._analysis_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="web-learning")
        self.analysis_service = LearningAnalysisService()
        self.coach = ConversationCoach()
        self.processor = TurnProcessor(self.coach)
        self.expression_library = ExpressionLibrary()
        self.targeted_practice = TargetedPracticeService(self.expression_library)
        self._pending_practice_focus = None
        self._pending_practice_text = ""
        self.agent = AgentOrchestrator(
            action_executor=ActionExecutor(targeted_practice_handler=self._offer_targeted_practice)
        )
        self.useful_expressions: list[dict[str, Any]] = []
        self._expression_recommendation_count = 0

    def speak(self, text: str) -> dict[str, Any]:
        with self._speak_lock:
            return self._speak_locked(text)

    def _speak_locked(self, text: str) -> dict[str, Any]:
        if self.targeted_practice.state["active"]:
            return self._submit_practice_turn(text)
        speed_change = self._apply_voice_feedback(text)
        conversation_hint = self._conversation_hint(text, speed_change)
        coaching_item = self._next_coaching_context()
        coaching_context = "\n".join(item for item in (
            coaching_item["prompt"] if coaching_item else "",
            conversation_hint,
        ) if item)
        with self._lock:
            turn_id = len(self.turns) + 1
        context = TurnContext(session_id=self.session_id, turn_id=turn_id,
                              phase="conversation", user_text=text,
                               duration_minutes=self.duration, topic=self.topic or "general conversation",
                               language_mode="english_only" if self.english_only else "auto",
                               coach_mode=self.mode, feedback_intensity=self.feedback_intensity,
                               session_difficulty=self.difficulty,
                               professional_context=self._professional_context(),
                               coaching_context=coaching_context)
        result = self.processor.process(context)
        self._pending_practice_text = text
        self._pending_practice_focus = self._practice_candidate(result, text)
        action_result = self.agent.run(
            result, mode=self.mode,
            session_context={"professional_relevance": self.mode == "business_coach"},
            error_memory=self.coach.error_memory,
            naturalness_memory=self.coach.naturalness_memory,
        )
        if coaching_item and not result.system_error:
            self._consume_coaching_context(coaching_item["id"])
        item = {"turn": context.turn_id, "user": text, "reply": result.reply,
                "action": action_result.action.value, "executed": action_result.executed,
                "reason": action_result.reason, "system_error": result.system_error,
                "asr_uncertain": bool(result.asr_uncertainty),
                "practice": self.practice_payload()}
        with self._lock:
            self.turns.append(item)
            if not result.system_error:
                if self._allows_live_teaching():
                    self._record_coaching_context(action_result)
                self._record_expression_candidate(result, text)
                if (self._pending_practice_focus and self._allows_practice()
                        and not self.targeted_practice.state["candidate"]):
                    self.targeted_practice.offer(self._pending_practice_focus)
                    item["practice"] = self.practice_payload()
        self._pending_practice_focus = None
        self._pending_practice_text = ""
        if not result.system_error:
            snapshot = {
                "session_id": self.session_id,
                "turn_id": context.turn_id,
                "user_text": text,
                "assistant_text": result.reply,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "asr_uncertainty": [item.model_dump() for item in result.asr_uncertainty],
                "naturalness": result.naturalness.model_dump(),
            }
            self._analysis_executor.submit(self._analyze_snapshot, snapshot)
        return item

    def _offer_targeted_practice(self, _decision):
        if not self._allows_practice():
            return None
        focus = self._pending_practice_focus or self.targeted_practice.expression_candidate(
            self._pending_practice_text, self.topic or "general conversation", self.difficulty
        )
        if self.mode == "business_coach" and not self._professional_expression_matches(
                self._pending_practice_text
        ):
            return None
        return self.targeted_practice.offer(focus)

    def _allows_live_teaching(self) -> bool:
        return self.mode == "teacher"

    def _allows_practice(self) -> bool:
        return self.mode == "teacher" or (
            self.mode == "business_coach" and self._professional_expression_matches(
                self._pending_practice_text
            )
        )

    def _practice_candidate(self, result, text: str):
        if not self._allows_practice():
            return None
        return self.targeted_practice.candidate_for(
            result, text, self.topic or "general conversation", self.difficulty
        )

    def _professional_expression_matches(self, text: str) -> bool:
        if self.mode != "business_coach":
            return False
        return any(
            entry.get("formality") != "casual" and "work" in entry.get("situations", [])
            for entry in self.expression_library.find_relevant(
                text, topic=self.topic or "work", level=self.difficulty, limit=3
            )
        )

    def _professional_context(self) -> str:
        if self.mode != "business_coach":
            return ""
        topic = (self.topic or "").lower()
        if "interview" in topic:
            return "Act as the interviewer. Explore the learner's experience, decisions, and results."
        if "presentation" in topic:
            return "Act as an engaged audience member. Ask practical questions about the message and evidence."
        if any(word in topic for word in ("client", "customer", "sales", "negotiation")):
            return "Act as a professional counterpart. Clarify needs, trade-offs, and next steps."
        if any(word in topic for word in ("meeting", "project", "team", "work", "office", "business")):
            return "Act as a professional colleague. Discuss goals, progress, decisions, and next steps."
        return "Act as a professional conversation partner. Establish a plausible workplace context and a clear purpose naturally."

    def _submit_practice_turn(self, text: str) -> dict[str, Any]:
        outcome = self.targeted_practice.submit(text)
        return {
            "turn": len(self.turns) + 1, "user": text,
            "reply": self.targeted_practice.prompt() if outcome["active"] else "Nice work. Let's return to our conversation.",
            "action": "targeted_practice", "executed": True, "reason": "session practice",
            "system_error": False, "asr_uncertain": False, "practice": self.practice_payload(),
        }

    def practice_payload(self):
        state = self.targeted_practice.state
        focus = state["focus"] or state["candidate"]
        return {
            "active": state["active"], "candidate": state["candidate"], "step": state["step"],
            "focus": focus, "prompt": self.targeted_practice.prompt(), "result": state["result"],
        }

    def start_practice(self):
        self.targeted_practice.start()
        return self.practice_payload()

    def skip_practice(self):
        self.targeted_practice.skip()
        return self.practice_payload()

    def _apply_voice_feedback(self, text: str) -> str | None:
        """在本 Session 内调整语速，不触碰浏览器永久设置。"""
        normalized = " ".join((text or "").lower().split())
        too_fast = any(phrase in normalized for phrase in (
            "you're speaking too fast", "you are speaking too fast", "too fast",
            "can you speak slower", "could you speak slower", "please slow down",
            "speak more slowly", "a little slower", "you're talking too fast",
        ))
        faster = any(phrase in normalized for phrase in (
            "you can speak faster", "speak a little faster", "you can talk faster",
        ))
        if too_fast and not faster:
            self.session_voice_rate = max(0.7, round(self.session_voice_rate - 0.1, 1))
            self.tts_rate = edge_tts_rate(self.session_voice_rate)
            return "The learner asked you to speak more slowly. Briefly acknowledge this and keep the reply short."
        if faster and not too_fast:
            self.session_voice_rate = min(1.2, round(self.session_voice_rate + 0.1, 1))
            self.tts_rate = edge_tts_rate(self.session_voice_rate)
            return "The learner asked you to speak a little faster. Briefly acknowledge this and keep the reply short."
        return None

    @staticmethod
    def _conversation_hint(text: str, speed_change: str | None) -> str:
        normalized = " ".join((text or "").lower().split())
        if any(phrase in normalized for phrase in ("what does that mean", "can you explain", "i don't understand", "what do you mean")):
            return "The learner needs a brief, simple explanation and one example, then return to the current topic without adding a lesson."
        if any(phrase in normalized for phrase in ("this conversation is over", "let's stop", "i want to stop", "see you next time", "that's all for today")):
            return "The learner is ending the session. Respond warmly and close naturally; do not ask a new follow-up question."
        return speed_change or ""

    def _next_coaching_context(self):
        with self._lock:
            return next((item for item in self.coaching_context if not item["consumed"]), None)

    def _consume_coaching_context(self, context_id):
        with self._lock:
            for item in self.coaching_context:
                if item["id"] == context_id:
                    item["consumed"] = True
                    return

    def _record_coaching_context(self, action_result):
        action = getattr(action_result.action, "value", action_result.action)
        prompts = {
            "gentle_feedback": (
                "If it fits naturally, offer one short, helpful conversational expression "
                "suggestion. Do not interrupt the conversation or give a lesson."
            ),
            "review_later": (
                "Keep the conversation natural. A previous expression may be worth briefly "
                "revisiting later only if it fits the conversation."
            ),
        }
        prompt = prompts.get(action)
        if not prompt:
            return
        self._coaching_context_counter += 1
        self.coaching_context.append({
            "id": self._coaching_context_counter,
            "action": action,
            "prompt": prompt,
            "consumed": False,
        })

    def _record_expression_candidate(self, result, text):
        """将自然度信号转换成一个可选的下一轮教学提示。"""
        if self.mode == "foreign_friend":
            return
        if self._expression_recommendation_count >= 3:
            return
        signal = result.naturalness
        if not getattr(signal, "detected", False):
            return
        candidates = self.expression_library.find_relevant(
            text, topic=self.topic or "general conversation", level=self.difficulty,
            limit=3 if self.mode == "business_coach" else 1
        )
        if self.mode == "business_coach":
            candidates = [entry for entry in candidates
                          if entry.get("formality") != "casual" and "work" in entry.get("situations", [])]
        if not candidates:
            return
        candidate = candidates[0]
        self._expression_recommendation_count += 1
        expression = {
            "expression": candidate["expression"],
            "meaning": candidate["meaning"],
            "example": candidate["examples"][0] if candidate["examples"] else "",
            "turn": len(self.turns),
        }
        self.useful_expressions.append(expression)
        self._coaching_context_counter += 1
        self.coaching_context.append({
            "id": self._coaching_context_counter,
            "action": "native_expression",
            "prompt": (
                f'A natural expression that may fit this conversation is: "{candidate["expression"]}". '
                "Use it only if it fits naturally. Do not force a correction or give a lesson."
            ),
            "consumed": False,
        })

    def _analyze_snapshot(self, snapshot):
        try:
            record = self.analysis_service.analyze(snapshot)
        except Exception as exc:
            record = {
                "session_id": snapshot["session_id"],
                "turn_id": snapshot["turn_id"],
                "status": "failed",
                "error": str(exc),
            }
        with self._lock:
            self.learning_analysis = [
                item for item in self.learning_analysis
                if item["turn_id"] != record["turn_id"]
            ]
            self.learning_analysis.append(record)
            self.learning_analysis.sort(key=lambda item: item["turn_id"])

    def review(self) -> dict[str, Any]:
        with self._lock:
            turns = list(self.turns)
            analyses = list(self.learning_analysis)
        valid = [item for item in turns if not item["system_error"]]
        if not valid:
            return {
                "session_id": self.session_id,
                "topic": self.topic,
                "mode": self.mode,
                "turn_count": 0,
                "summary": "本次没有完成可供复盘的对话。",
                "highlights": [],
                "vocabulary": [],
                "naturalness": [],
                "asr_notes": [],
                "coaching_notes": [],
                "useful_expressions": [],
                "practiced_expressions": [],
                "next_focus": "下次可以从一句简短的英语表达开始。",
                "insights_preparing": False,
                "actions": [],
            }

        by_turn = {item.get("turn_id"): item for item in analyses}
        valid_ids = {item["turn"] for item in valid}
        completed = [by_turn[turn_id] for turn_id in valid_ids
                     if by_turn.get(turn_id, {}).get("status") == "completed"]
        insights_preparing = len(completed) < len(valid_ids)
        useful_words = sorted({word for item in completed
                               for word in item.get("vocabulary", {}).get("useful_words", [])})
        repeated_words = sorted({word for item in completed
                                 for word in item.get("vocabulary", {}).get("repeated_words", [])})
        naturalness = []
        asr_notes = []
        for item in completed:
            signal = item.get("naturalness") or {}
            if signal.get("detected") and signal.get("alternatives"):
                naturalness.append({
                    "original": signal.get("original", ""),
                    "alternatives": list(signal.get("alternatives") or []),
                    "explanation": signal.get("explanation", ""),
                })
            if item.get("possible_asr_issue"):
                asr_notes.append(
                    f"第 {item.get('turn_id')} 轮中，语音识别器可能对部分内容不够确定。"
                )

        highlights = [f"你完成了 {len(valid)} 轮英语对话，并持续补充了自己的想法。"]
        if useful_words:
            highlights.append(f"本次对话中使用了 {len(useful_words)} 个值得保留的词汇。")
        coaching_notes = []
        if any(item["action"] == "review_later" for item in valid):
            coaching_notes.append("有些内容已保留到本次复盘中。")
        if any(item["action"] == "gentle_feedback" for item in valid):
            coaching_notes.append("本次对话中有值得继续留意的轻量表达提示。")
        if repeated_words:
            next_focus = f"下次试着用不同方式表达“{repeated_words[0]}”相关的想法。"
        elif naturalness:
            next_focus = "下次试着在对话中使用一种更自然的替代表达。"
        else:
            next_focus = "下次继续围绕主题补充一个具体细节或例子。"
        return {
            "session_id": self.session_id,
            "topic": self.topic,
            "mode": self.mode,
            "turn_count": len(valid),
            "summary": f"本次完成了 {len(valid)} 轮英语对话。" if self.topic is None else f"本次完成了 {len(valid)} 轮围绕“{self.topic}”的对话。",
            "highlights": highlights,
            "vocabulary": {
                "useful_words": useful_words,
                "repeated_words": repeated_words,
            },
            "naturalness": naturalness,
            "asr_notes": asr_notes,
            "coaching_notes": coaching_notes,
            "useful_expressions": list(self.useful_expressions),
            "practiced_expressions": list(self.targeted_practice.results),
            "next_focus": next_focus,
            "insights_preparing": insights_preparing,
            "actions": [item["action"] for item in valid],
        }


class WebState:
    def __init__(self):
        self.sessions: dict[str, WebSession] = {}
        self.lock = threading.Lock()

    def create(self, payload):
        session = WebSession(payload)
        with self.lock:
            self.sessions[session.session_id] = session
        return session

    def get(self, session_id):
        with self.lock:
            return self.sessions.get(session_id)


STATE = WebState()


class Handler(BaseHTTPRequestHandler):
    server_version = "SpeakingCoachWeb/0.1"

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            return self._file("index.html", "text/html; charset=utf-8")
        if self.path.startswith("/assets/"):
            name = self.path.removeprefix("/assets/")
            if name in {"styles.css", "app.js"}:
                kind = "text/css; charset=utf-8" if name.endswith("css") else "text/javascript; charset=utf-8"
                return self._file(name, kind)
        if self.path.startswith("/api/session/") and self.path.endswith("/review"):
            session = STATE.get(self.path.split("/")[3])
            return self._json(session.review() if session else {"error": "session not found"}, 200 if session else 404)
        if self.path.startswith("/api/session/") and self.path.endswith("/practice"):
            session = STATE.get(self.path.split("/")[3])
            return self._json(session.practice_payload() if session else {"error": "session not found"}, 200 if session else 404)
        return self._json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path.startswith("/api/session/") and self.path.endswith("/practice/start"):
            session = STATE.get(self.path.split("/")[3])
            return self._json(session.start_practice() if session else {"error": "session not found"}, 200 if session else 404)
        if self.path.startswith("/api/session/") and self.path.endswith("/practice/skip"):
            session = STATE.get(self.path.split("/")[3])
            return self._json(session.skip_practice() if session else {"error": "session not found"}, 200 if session else 404)
        if self.path.startswith("/api/session/") and self.path.endswith("/audio"):
            return self._upload_audio(self.path.split("/")[3])
        if self.path.startswith("/api/session/") and self.path.endswith("/tts"):
            return self._synthesize_tts(self.path.split("/")[3])
        payload = self._body()
        if self.path == "/api/session":
            session = STATE.create(payload)
            return self._json({"session_id": session.session_id, "topic": session.topic, "mode": session.mode,
                               "difficulty": session.difficulty, "duration": session.duration})
        if self.path.startswith("/api/session/") and self.path.endswith("/turn"):
            session = STATE.get(self.path.split("/")[3])
            if not session or not payload.get("text", "").strip():
                return self._json({"error": "session or text missing"}, 400)
            try:
                return self._json(session.speak(payload["text"].strip()))
            except Exception:
                return self._json({"error": "Something went wrong. Let's try that again."}, 502)
        return self._json({"error": "not found"}, 404)

    def _upload_audio(self, session_id):
        session = STATE.get(session_id)
        if not session:
            return self._json({"error": "session not found"}, 404)
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0 or length > MAX_AUDIO_BYTES:
            return self._json({"error": "audio file is missing or too large"}, 413)
        content_type = self.headers.get("Content-Type", "")
        if not content_type.startswith("multipart/form-data"):
            return self._json({"error": "multipart audio upload required"}, 415)
        try:
            body = self.rfile.read(length)
            message = BytesParser(policy=default).parsebytes(
                f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode() + body
            )
            item = next((part for part in message.walk()
                         if part.get_param("name", header="content-disposition") == "audio"), None)
            media_type = (item.get_content_type() if item else "").lower()
            payload = item.get_payload(decode=True) if item else b""
        except (TypeError, ValueError):
            return self._json({"error": "audio field is missing"}, 400)
        if media_type not in ALLOWED_AUDIO_TYPES:
            return self._json({"error": "unsupported audio type"}, 415)
        if not payload or len(payload) > MAX_AUDIO_BYTES:
            return self._json({"error": "audio file is missing or too large"}, 413)
        suffix = {"audio/webm": ".webm", "audio/ogg": ".ogg", "audio/wav": ".wav",
                  "audio/x-wav": ".wav", "audio/mpeg": ".mp3"}[media_type]
        target_dir = AUDIO_ROOT / session_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{uuid4().hex}{suffix}"
        target.write_bytes(payload)
        try:
            transcription = transcribe_uploaded_audio(target)
        except FfmpegUnavailableError:
            return self._json({"error": "FFmpeg is unavailable"}, 503)
        except AudioConversionError:
            return self._json({"error": "FFmpeg conversion failed"}, 422)
        except ValueError as exc:
            return self._json({"error": "transcription is empty", "detail": str(exc)}, 422)
        except Exception as exc:
            return self._json({"error": "Whisper is unavailable or transcription failed", "detail": str(exc)}, 503)
        try:
            # 音频转写成功后复用文本输入的唯一 Turn 入口，避免两条决策链。
            turn = session.speak(transcription)
        except Exception:
            return self._json({"error": "Something went wrong. Let's try that again."}, 502)
        return self._json({"upload_id": target.stem, "content_type": media_type,
                           "bytes": len(payload), "status": "transcribed",
                           "transcription": transcription, "turn": turn}, 201)

    def _synthesize_tts(self, session_id):
        session = STATE.get(session_id)
        if not session:
            return self._json({"error": "session not found"}, 404)
        if TTS_PROVIDER is None:
            return self._json({"error": "TTS is unavailable"}, 503)
        try:
            payload = self._body()
        except (TypeError, ValueError, json.JSONDecodeError):
            return self._json({"error": "invalid TTS request"}, 400)
        text = payload.get("text", "") if isinstance(payload, dict) else ""
        if not isinstance(text, str) or not text.strip():
            return self._json({"error": "text is required"}, 400)
        try:
            provider = TTS_PROVIDER
            if isinstance(provider, EdgeTTSProvider):
                provider = EdgeTTSProvider(voice=session.voice_name, rate=session.tts_rate)
            result = provider.synthesize(text.strip())
            if not isinstance(result.audio, bytes) or not result.audio or not result.content_type:
                raise ValueError("empty TTS result")
            return self._binary(result.audio, result.content_type)
        except Exception:
            return self._json({"error": "TTS synthesis failed"}, 503)

    def _body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length) or b"{}")

    def _file(self, name, content_type):
        path = WEB_ROOT / name if name == "index.html" else WEB_ROOT / "assets" / name
        if not path.exists():
            return self._json({"error": "not found"}, 404)
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _json(self, data, status=200):
        content = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _binary(self, content, content_type, status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, *_):
        return


def run(host="127.0.0.1", port=8000):
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Speaking Coach Web UI: http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
