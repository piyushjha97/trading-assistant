from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


@dataclass(frozen=True)
class SignalInput:
    candidate_id: str
    direction: Literal["BUY", "SELL"]
    evidence: Mapping[str, Decimal]


class SignalAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    candidate_id: str
    decision: Literal["APPROVE", "ABSTAIN"]
    evidence_ids: tuple[str, ...] = Field(max_length=8)


class SignalModel(Protocol):
    def assess(self, evidence: SignalInput) -> SignalAssessment | None: ...


class NoOpSignalModel:
    """Use the deterministic baseline while no model is configured."""

    def assess(self, evidence: SignalInput) -> None:
        return None
