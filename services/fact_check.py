from domain.claim_analysis import AnalyzeResponse, ClaimResult, extract_claims
from engines.classifier import ClaimClassifier
from engines.evidence import EvidenceEngine

MAX_CLAIMS_PER_ARTICLE = 8


class FactCheckService:
    def __init__(
        self,
        evidence_engine: EvidenceEngine | None = None,
        classifier: ClaimClassifier | None = None,
    ) -> None:
        self.evidence_engine = evidence_engine or EvidenceEngine()
        self.classifier = classifier or ClaimClassifier()

    def analyze(self, text: str) -> AnalyzeResponse:
        extracted_claims = extract_claims(text)
        analysis_limited = len(extracted_claims) > MAX_CLAIMS_PER_ARTICLE
        claims = extracted_claims[:MAX_CLAIMS_PER_ARTICLE]
        if not claims:
            return AnalyzeResponse(
                verdict="uncertain",
                summary="No checkable claim was found in the submitted text.",
                results=[],
            )

        results: list[ClaimResult] = []
        for claim in claims:
            evidence = self.evidence_engine.retrieve(claim.text)
            results.append(
                self.classifier.classify(claim.text, claim.signals, evidence)
            )

        verdicts = {result.verdict for result in results}
        if verdicts == {"supported"}:
            verdict = "supported"
            summary = "All extracted claims are supported by the available evidence."
        elif verdicts == {"refuted"}:
            verdict = "refuted"
            summary = "All extracted claims are contradicted by the available evidence."
        elif verdicts <= {"supported", "refuted", "mixed"} and (
            "mixed" in verdicts or len(verdicts) > 1
        ):
            verdict = "mixed"
            summary = "The available evidence supports some claims and contradicts others."
        else:
            verdict = "uncertain"
            summary = "There is not enough independent evidence to reach a reliable verdict."

        if analysis_limited:
            summary = f"Only the first {MAX_CLAIMS_PER_ARTICLE} claims were analyzed. {summary}"
        return AnalyzeResponse(
            verdict=verdict,
            summary=summary,
            results=results,
            analysis_limited=analysis_limited,
        )
