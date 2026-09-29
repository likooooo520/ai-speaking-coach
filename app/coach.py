from typing import Optional, List

from pydantic import BaseModel, Field


class Correction(BaseModel):

    needed: bool = False

    original: Optional[str] = None

    better: Optional[str] = None

    explanation: Optional[str] = None


class ASRUncertainty(BaseModel):

    heard: str

    possible: Optional[str] = None

    confidence: str = "low"


class NaturalnessSuggestion(BaseModel):

    detected: bool = False

    original: Optional[str] = None

    alternatives: List[str] = Field(
        default_factory=list
    )

    explanation: Optional[str] = None

    category: str = "expression"


class Performance(BaseModel):

    fluency: float = 0.0

    grammar: float = 0.0

    vocabulary: float = 0.0

    naturalness: float = 0.0

    overall: float = 0.0

    band: str = "normal"

    suggested_action: str = "maintain"


class CoachDecision(BaseModel):

    reply: str = ""

    # True = 当前不是一次有效的 Coach 分析，
    # 而是系统 / API 故障。
    system_error: bool = False

    correction: Correction = Field(
        default_factory=Correction
    )

    asr_uncertainty: List[
        ASRUncertainty
    ] = Field(
        default_factory=list
    )

    naturalness: NaturalnessSuggestion = Field(
        default_factory=NaturalnessSuggestion
    )

    performance: Performance = Field(
        default_factory=Performance
    )

    conversation_topic: str = (
        "general conversation"
    )

    difficulty: str = "B2"

    next_action: str = (
        "continue_conversation"
    )