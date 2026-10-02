import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from domain.claim_analysis import Claim, ClaimResult, EvidenceItem
from engines.classifier import ClaimClassifier
from engines.evidence import EvidenceEngine
from services.fact_check import FactCheckService


client = TestClient(app)


@pytest.fixture(autouse=True)
def disable_external_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    service = FactCheckService(
        evidence_engine=EvidenceEngine(api_key=""),
        classifier=ClaimClassifier(api_key=""),
    )
    monkeypatch.setattr("app.main.service", service)


class AssessmentResponseStub:
    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict[str, object]:
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "rationale": "Two independent reports state the same fact.",
                                "confidence": 0.82,
                                "evidence_assessments": [
                                    {"index": 0, "stance": "supports"},
                                    {"index": 1, "stance": "supports"},
                                ],
                            }
                        )
                    }
                }
            ]
        }


class AssessmentClientStub:
    def post(self, url: str, **kwargs: object) -> AssessmentResponseStub:
        assert url.endswith("/chat/completions")
        assert kwargs["json"]["response_format"] == {"type": "json_object"}
        return AssessmentResponseStub()


def test_analysis_abstains_without_independent_evidence() -> None:
    response = client.post(
        "/analyze",
        json={"text": "The city opened a new public library in 2024."},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["verdict"] == "uncertain"
    assert result["results"][0]["verdict"] == "uncertain"
    assert result["results"][0]["confidence"] == 0.0
    assert result["results"][0]["evidence"] == []


def test_extracts_multiple_claims_and_review_signals() -> None:
    response = client.post(
        "/analyze",
        json={"text": "Everyone agrees. The report counted 12 new clinics."},
    )

    result = response.json()
    assert len(result["results"]) == 2
    assert "absolute_language" in result["results"][0]["claim"]["signals"]
    assert "contains_quantitative_detail" in result["results"][1]["claim"]["signals"]


def test_service_uses_retrieved_evidence() -> None:
    class EvidenceStub:
        def retrieve(self, claim: str) -> list[EvidenceItem]:
            return [EvidenceItem(source="test", snippet="Verified record")]

    class ClassifierStub:
        def classify(
            self, claim: str, signals: list[str], evidence: list[EvidenceItem]
        ) -> ClaimResult:
            return ClaimResult(
                claim=Claim(text=claim, signals=signals),
                verdict="supported",
                confidence=0.8,
                rationale="The injected test classifier supports the claim.",
                evidence=evidence,
            )

    result = FactCheckService(
        evidence_engine=EvidenceStub(), classifier=ClassifierStub()
    ).analyze(
        "The record confirms the event occurred."
    )

    assert result.verdict == "supported"
    assert result.results[0].confidence == 0.8


def test_rejects_empty_text() -> None:
    response = client.post("/analyze", json={"text": ""})

    assert response.status_code == 422


def test_serves_frontend_and_script() -> None:
    assert client.get("/").status_code == 200
    script = client.get("/frontend/app.js")

    assert script.status_code == 200
    assert "analyze-form" in script.text


def test_tavily_retrieval_returns_cited_evidence() -> None:
    class ResponseStub:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict[str, object]:
            return {
                "results": [
                    {
                        "title": "Official report",
                        "url": "https://example.org/report",
                        "content": "The report records the event.",
                        "score": 0.92,
                        "published_date": "2026-01-10",
                    }
                ]
            }

    class ClientStub:
        def post(self, url: str, **kwargs: object) -> ResponseStub:
            assert url == EvidenceEngine.endpoint
            assert kwargs["headers"] == {"Authorization": "Bearer test-key"}
            assert kwargs["json"]["include_answer"] is False
            return ResponseStub()

    evidence = EvidenceEngine(api_key="test-key", client=ClientStub()).retrieve(
        "The report recorded the event."
    )

    assert len(evidence) == 1
    assert evidence[0].source == "Official report"
    assert evidence[0].url == "https://example.org/report"
    assert evidence[0].relevance_score == 0.92


def test_classifier_requires_two_distinct_hosts_to_support_claim() -> None:
    evidence = [
        EvidenceItem(
            source="Report one",
            snippet="The event happened.",
            url="https://news-one.example/report",
            relevance_score=0.9,
        ),
        EvidenceItem(
            source="Report two",
            snippet="The event happened.",
            url="https://news-two.example/report",
            relevance_score=0.8,
        ),
    ]
    classifier = ClaimClassifier(api_key="test-key", client=AssessmentClientStub())

    result = classifier.classify("The event happened.", [], evidence)

    assert result.verdict == "supported"
    assert result.confidence == 0.82
    assert [item.supports for item in result.evidence] == ["supports", "supports"]


def test_classifier_abstains_when_only_one_host_supports_claim() -> None:
    evidence = [
        EvidenceItem(
            source="One report",
            snippet="The event happened.",
            url="https://one.example/report",
            relevance_score=0.9,
        )
    ]
    classifier = ClaimClassifier(api_key="test-key", client=AssessmentClientStub())

    result = classifier.classify("The event happened.", [], evidence)

    assert result.verdict == "uncertain"
    assert "corroboration" in result.rationale
