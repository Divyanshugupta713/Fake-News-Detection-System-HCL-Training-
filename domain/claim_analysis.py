from typing import Literal

from pydantic import BaseModel, Field


Verdict = Literal["supported", "refuted", "mixed", "uncertain"]


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20_000)


class Claim(BaseModel):
    text: str
    signals: list[str] = Field(default_factory=list)


class EvidenceItem(BaseModel):
    source: str
    snippet: str
    url: str = ""
    published_at: str | None = None
    relevance_score: float = Field(default=0, ge=0, le=1)
    supports: Literal["supports", "contradicts", "context"] = "context"


class ClaimResult(BaseModel):
    claim: Claim
    verdict: Verdict
    confidence: float = Field(ge=0, le=1)
    confidence_note: str = "Model-estimated, not a calibrated probability."
    rationale: str
    evidence: list[EvidenceItem] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    verdict: Verdict
    summary: str
    results: list[ClaimResult]
    analysis_limited: bool = False


def extract_claims(text: str) -> list[Claim]:
    """Split input into sentence-like claims and attach review signals."""
    import re

    pieces = [part.strip() for part in re.split(r"(?<=[.!?])\s+|[\r\n]+", text)]
    claims: list[Claim] = []
    for piece in pieces:
        normalized = " ".join(piece.split())
        if not normalized:
            continue
        lowered = normalized.casefold()
        signals: list[str] = []
        if any(term in lowered.split() for term in ("always", "never", "everyone", "nobody")):
            signals.append("absolute_language")
        if any(char.isdigit() for char in normalized):
            signals.append("contains_quantitative_detail")
        if len(normalized.split()) < 4:
            signals.append("very_short_claim")
        claims.append(Claim(text=normalized, signals=signals))
    return claims
