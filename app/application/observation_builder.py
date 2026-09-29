from app.domain.evidence import Evidence, ErrorEvidence, NaturalnessEvidence
from app.domain.observation import Observation
from app.domain.turn import TurnResult


class ObservationBuilder:
    """只组装 TurnResult 与已有只读记忆事实，不产生副作用。"""

    def build(self, result: TurnResult, error_memory=None, naturalness_memory=None,
              user_requested=None, session_relevance=None, interruption_cost=None):
        if result.system_error:
            return None, None
        correction = result.correction
        error_match = self._match(error_memory, "error", correction.original if correction.needed else None)
        naturalness = result.naturalness
        naturalness_match = self._match(naturalness_memory, "expression", naturalness.original if naturalness.detected else None)
        observation = Observation(
            session_id=result.context.session_id, turn_id=result.context.turn_id,
            phase=result.context.phase, user_text=result.context.user_text,
            correction=correction, naturalness=naturalness,
            asr_uncertainty=result.asr_uncertainty, performance=result.performance,
            topic=result.context.topic or result.conversation_topic,
        )
        evidence = Evidence(
            error=ErrorEvidence(current_error_detected=bool(correction.needed),
                                historical_match=error_match[0], historical_frequency=error_match[1],
                                user_requested=user_requested, asr_uncertain=bool(result.asr_uncertainty)),
            naturalness=NaturalnessEvidence(current_naturalness_detected=bool(naturalness.detected),
                                            historical_match=naturalness_match[0], historical_frequency=naturalness_match[1],
                                            user_requested=user_requested),
            session_relevance=session_relevance, interruption_cost=interruption_cost,
        )
        return observation, evidence

    @staticmethod
    def _match(memory, kind, original):
        if memory is None or not original:
            return False, 0
        matcher = getattr(memory, f"match_current_{kind}", None)
        frequency = getattr(memory, f"get_{kind}_frequency", None)
        if matcher is None or frequency is None:
            return False, 0
        return matcher(original) is not None, frequency(original)
