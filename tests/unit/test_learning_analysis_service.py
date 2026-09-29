import unittest

from app.application.learning_analysis_service import LearningAnalysisService


class LearningAnalysisServiceTests(unittest.TestCase):
    def snapshot(self, **updates):
        value = {
            "session_id": "session-1",
            "turn_id": 1,
            "user_text": "I usually practice useful vocabulary vocabulary.",
            "assistant_text": "That is a useful habit.",
            "timestamp": "2026-01-01T00:00:00+00:00",
            "asr_uncertainty": [],
            "naturalness": {"detected": False},
        }
        value.update(updates)
        return value

    def test_collects_turn_data_and_vocabulary_without_external_writes(self):
        record = LearningAnalysisService().analyze(self.snapshot())

        self.assertEqual(record["raw_transcription"], self.snapshot()["user_text"])
        self.assertEqual(record["assistant_text"], "That is a useful habit.")
        self.assertIn("vocabulary", record["vocabulary"]["repeated_words"])
        self.assertEqual(record["status"], "completed")

    def test_asr_evidence_is_recorded_without_changing_raw_text(self):
        raw = "I spoke with the call walks."
        evidence = [{"heard": "call walks", "possible": "coworkers", "confidence": "medium"}]
        record = LearningAnalysisService().analyze(self.snapshot(user_text=raw, asr_uncertainty=evidence))

        self.assertTrue(record["possible_asr_issue"])
        self.assertEqual(record["raw_transcription"], raw)
        self.assertEqual(record["asr_evidence"], evidence)

    def test_naturalness_and_vocabulary_are_independent_of_reply(self):
        record = LearningAnalysisService().analyze(self.snapshot(
            assistant_text="That sounds interesting.",
            naturalness={"detected": True, "original": "I want improve", "alternatives": ["I want to improve"]},
        ))

        self.assertTrue(record["naturalness"]["detected"])
        self.assertEqual(record["assistant_text"], "That sounds interesting.")

if __name__ == "__main__":
    unittest.main()
