import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.coach import CoachDecision
from app.domain.action import ActionResult
from app.domain.decision import AgentAction
from app.domain.turn import TurnContext, TurnResult
from app.application.turn_processor import TurnProcessor
from app.web import WebSession


class InlineExecutor:
    def submit(self, function, snapshot):
        function(snapshot)


class WebLearningAnalysisTests(unittest.TestCase):
    def make_session(self):
        with patch("app.web.ConversationCoach") as coach_type:
            session = WebSession({"topic": "work"})
        session._analysis_executor.shutdown(wait=True)
        session._analysis_executor = InlineExecutor()
        session.processor = MagicMock()
        session.agent = MagicMock()
        session.processor.process.return_value = TurnResult(
            context=TurnContext(session_id=session.session_id, turn_id=1, phase="conversation", user_text="hello"),
            decision=CoachDecision(reply="Nice to meet you."),
        )
        session.agent.run.return_value = ActionResult(action=AgentAction.CONTINUE, executed=True, reason="continue")
        return session

    def test_successful_turn_collects_analysis_without_changing_reply(self):
        session = self.make_session()

        item = session.speak("hello")

        self.assertFalse(item["system_error"])
        self.assertEqual(item["reply"], "Nice to meet you.")
        self.assertEqual(len(session.learning_analysis), 1)
        self.assertEqual(session.learning_analysis[0]["raw_transcription"], "hello")

    def test_web_session_passes_mode_and_feedback_intensity_to_coach(self):
        session = self.make_session()
        session.mode = "business_coach"
        session.feedback_intensity = "strong"

        session.speak("hello")

        self.assertEqual(
            session.coach.set_session_context.call_args.kwargs["coach_mode"],
            "business_coach",
        )
        self.assertEqual(
            session.coach.set_session_context.call_args.kwargs["feedback_intensity"],
            "strong",
        )

    def test_analysis_failure_does_not_fail_turn(self):
        session = self.make_session()
        session.analysis_service.analyze = MagicMock(side_effect=RuntimeError("analysis unavailable"))

        item = session.speak("hello")

        self.assertFalse(item["system_error"])
        self.assertEqual(session.learning_analysis[0]["status"], "failed")
        self.assertEqual(session.learning_analysis[0]["turn_id"], 1)

    def test_records_are_sorted_when_analysis_completes_out_of_order(self):
        session = self.make_session()
        session.analysis_service.analyze = lambda snapshot: {
            "turn_id": snapshot["turn_id"], "session_id": snapshot["session_id"], "status": "completed"
        }
        first = {"session_id": session.session_id, "turn_id": 1}
        second = {"session_id": session.session_id, "turn_id": 2}
        threads = [
            threading.Thread(target=session._analyze_snapshot, args=(second,)),
            threading.Thread(target=session._analyze_snapshot, args=(first,)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual([item["turn_id"] for item in session.learning_analysis], [1, 2])

    def test_speak_pipeline_has_session_serialization_boundary(self):
        session = self.make_session()

        self.assertIsInstance(session._speak_lock, type(threading.Lock()))

    def test_review_falls_back_when_no_valid_turn_exists(self):
        session = self.make_session()
        session.turns = [{"turn": 1, "system_error": True, "action": "continue"}]

        review = session.review()

        self.assertEqual(review["turn_count"], 0)
        self.assertFalse(review["insights_preparing"])
        self.assertEqual(review["highlights"], [])

    def test_review_marks_pending_analysis_without_failing(self):
        session = self.make_session()
        session.turns = [{"turn": 1, "system_error": False, "action": "continue"}]

        review = session.review()

        self.assertEqual(review["turn_count"], 1)
        self.assertTrue(review["insights_preparing"])
        self.assertIn("1 轮", review["summary"])

    def test_review_uses_vocabulary_naturalness_and_asr_as_session_signals(self):
        session = self.make_session()
        session.turns = [
            {"turn": 1, "system_error": False, "action": "review_later"},
            {"turn": 2, "system_error": False, "action": "gentle_feedback"},
        ]
        session.learning_analysis = [
            {
                "turn_id": 1,
                "status": "completed",
                "possible_asr_issue": True,
                "vocabulary": {"useful_words": ["refreshing"], "repeated_words": ["water"]},
                "naturalness": {"detected": True, "original": "very good", "alternatives": ["really enjoyable"]},
            },
            {
                "turn_id": 2,
                "status": "completed",
                "possible_asr_issue": False,
                "vocabulary": {"useful_words": ["preference"], "repeated_words": []},
                "naturalness": {"detected": False},
            },
        ]

        review = session.review()

        self.assertFalse(review["insights_preparing"])
        self.assertEqual(review["vocabulary"]["useful_words"], ["preference", "refreshing"])
        self.assertEqual(review["vocabulary"]["repeated_words"], ["water"])
        self.assertEqual(review["naturalness"][0]["alternatives"], ["really enjoyable"])
        self.assertIn("语音识别器", review["asr_notes"][0])
        self.assertIn("water", review["next_focus"])
        self.assertTrue(review["coaching_notes"])

    def test_system_error_turn_does_not_contribute_to_review_signals(self):
        session = self.make_session()
        session.turns = [
            {"turn": 1, "system_error": True, "action": "review_later"},
            {"turn": 2, "system_error": False, "action": "continue"},
        ]
        session.learning_analysis = [{
            "turn_id": 1,
            "status": "completed",
            "possible_asr_issue": True,
            "vocabulary": {"useful_words": ["ignored"], "repeated_words": ["ignored"]},
            "naturalness": {"detected": False},
        }]

        review = session.review()

        self.assertEqual(review["turn_count"], 1)
        self.assertNotIn("ignored", review["vocabulary"]["useful_words"])
        self.assertEqual(review["asr_notes"], [])

    def test_review_does_not_invoke_long_term_learning_services(self):
        source = Path(__file__).resolve().parents[2] / "app" / "web.py"
        review_source = source.read_text(encoding="utf-8")
        review_source = review_source[review_source.index("    def review("):review_source.index("\n\n\nclass WebState")]

        for forbidden in ("LearningUpdateService", "add_error", "add_expression", "record(", "create_task"):
            self.assertNotIn(forbidden, review_source)

    def test_frontend_review_renders_real_fields_with_fallbacks(self):
        source = (Path(__file__).resolve().parents[2] / "web" / "assets" / "app.js").read_text(encoding="utf-8")
        review_source = source[source.index("function review(data)"):source.index("function escapeHtml")]

        for field in ("highlights", "vocabulary", "naturalness", "asr_notes", "next_focus", "insights_preparing"):
            self.assertIn(field, review_source)
        self.assertIn("safe.summary||t('review.fallbackSummary')", review_source)

    def test_continue_does_not_create_coaching_context(self):
        session = self.make_session()

        session.speak("hello")

        self.assertEqual(session.coaching_context, [])

    def test_gentle_feedback_is_available_to_the_next_turn_then_consumed(self):
        session = self.make_session()
        session.mode = "teacher"
        session.agent.run.return_value = ActionResult(
            action=AgentAction.GENTLE_FEEDBACK, executed=True, reason="feedback"
        )

        session.speak("first")
        self.assertEqual(len(session.coaching_context), 1)
        self.assertFalse(session.coaching_context[0]["consumed"])

        session.agent.run.return_value = ActionResult(
            action=AgentAction.CONTINUE, executed=True, reason="continue"
        )
        session.speak("second")

        context_values = [call.kwargs.get("coaching_context") for call in session.coach.set_session_context.call_args_list]
        self.assertIn(session.coaching_context[0]["prompt"], context_values)
        self.assertTrue(session.coaching_context[0]["consumed"])

    def test_review_later_is_deferred_without_changing_current_reply(self):
        session = self.make_session()
        session.mode = "teacher"
        session.agent.run.return_value = ActionResult(
            action=AgentAction.REVIEW_LATER, executed=True, reason="review"
        )

        item = session.speak("hello")

        self.assertEqual(item["reply"], "Nice to meet you.")
        self.assertEqual(session.coaching_context[0]["action"], "review_later")
        self.assertFalse(session.coaching_context[0]["consumed"])

    def test_system_error_does_not_record_coaching_context(self):
        session = self.make_session()
        session.processor.process.return_value = TurnResult(
            context=TurnContext(session_id=session.session_id, turn_id=1, phase="conversation", user_text="hello"),
            decision=CoachDecision(reply="I missed that.", system_error=True),
        )
        session.agent.run.return_value = ActionResult(
            action=AgentAction.GENTLE_FEEDBACK, executed=True, reason="feedback"
        )

        session.speak("hello")

        self.assertEqual(session.coaching_context, [])

    def test_task_and_targeted_practice_actions_do_not_create_context_or_mutate_tasks(self):
        session = self.make_session()
        for action in (AgentAction.TASK_FOLLOW_UP, AgentAction.TARGETED_PRACTICE):
            session.agent.run.return_value = ActionResult(action=action, executed=False, reason="unavailable")
            session.speak(action.value)
        self.assertEqual(session.coaching_context, [])

    def test_natural_chat_blocks_expression_coaching_and_practice_candidates(self):
        session = self.make_session()
        session.mode = "foreign_friend"
        session.processor.process.return_value = TurnResult(
            context=TurnContext(session_id=session.session_id, turn_id=1, phase="conversation", user_text="I very like it"),
            decision=CoachDecision(
                reply="I get why you like it.",
                naturalness={"detected": True, "alternatives": ["I really like it."], "explanation": "Natural phrasing"},
            ),
        )
        session.agent.run.return_value = ActionResult(
            action=AgentAction.TARGETED_PRACTICE, executed=False, reason="not available"
        )

        item = session.speak("I very like it")

        self.assertEqual(item["reply"], "I get why you like it.")
        self.assertEqual(session.coaching_context, [])
        self.assertEqual(session.useful_expressions, [])
        self.assertIsNone(session.targeted_practice.state["candidate"])
        self.assertIsNone(session._offer_targeted_practice(None))

    def test_teacher_mode_can_offer_a_practice_candidate(self):
        session = self.make_session()
        session.mode = "teacher"
        focus = {"type": "naturalness", "target": "I really like it."}
        session.targeted_practice.candidate_for = MagicMock(return_value=focus)

        session.speak("I very like it")

        self.assertEqual(session.targeted_practice.state["candidate"], focus)

    def test_teacher_learning_signal_reaches_practice_and_review(self):
        with patch("app.web.ConversationCoach") as coach_type:
            session = WebSession({"mode": "teacher", "topic": "food"})
        session._analysis_executor.shutdown(wait=True)
        session._analysis_executor = InlineExecutor()
        session.processor = TurnProcessor(session.coach)
        session.agent = MagicMock()
        session.coach.chat.return_value = CoachDecision(
            reply="Spicy sauce goes really well with burgers.",
            naturalness={
                "detected": True,
                "original": "I very like",
                "alternatives": ["I really like"],
                "explanation": "Use really before like.",
            },
        )
        session.agent.run.return_value = ActionResult(
            action=AgentAction.CONTINUE, executed=True, reason="continue"
        )

        item = session.speak("I very like spicy sauce.")
        review = session.review()

        self.assertEqual(item["practice"]["candidate"]["target"], "I really like")
        self.assertTrue(review["naturalness"][0]["alternatives"])

    def test_business_mode_builds_a_professional_role_from_topic(self):
        session = self.make_session()
        session.mode = "business_coach"
        session.topic = "job interview"

        session.speak("I led a small project.")

        kwargs = session.coach.set_session_context.call_args.kwargs
        self.assertEqual(kwargs["coach_mode"], "business_coach")
        self.assertEqual(kwargs["session_difficulty"], session.difficulty)
        self.assertIn("interviewer", kwargs["professional_context"])


if __name__ == "__main__":
    unittest.main()
