import unittest

from app.coach import Correction
from app.domain.evidence import Evidence
from app.domain.observation import Observation


class ObservationTests(unittest.TestCase):
    def test_observation_reuses_coach_models(self):
        correction = Correction(needed=True, original="many food", better="much food")
        observation = Observation(session_id="s1", turn_id=1, phase="conversation",
                                  user_text="I like many food", correction=correction)
        self.assertIs(observation.correction, correction)
        self.assertTrue(observation.is_valid)

    def test_evidence_defaults_are_independent(self):
        Evidence().error.historical_frequency = 3
        self.assertEqual(Evidence().error.historical_frequency, 0)
