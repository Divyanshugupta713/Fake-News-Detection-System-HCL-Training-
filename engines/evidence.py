import os
from typing import Any

import httpx

from domain.claim_analysis import EvidenceItem
from engines.errors import ExternalProviderError


class EvidenceEngine:
    """Retrieve source snippets from Tavily when an API key is configured."""

    endpoint = "https://api.tavily.com/search"

    def __init__(
        self, api_key: str | None = None, client: Any | None = None
    ) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("TAVILY_API_KEY", "")
        self.client = client

    def retrieve(self, claim: str) -> list[EvidenceItem]:
        if not self.api_key:
            return []

        try:
            if self.client is None:
                with httpx.Client(timeout=15) as client:
                    response = client.post(
                        self.endpoint,
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json=self._payload(claim),
                    )
            else:
                response = self.client.post(
                    self.endpoint,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=self._payload(claim),
                )
            response.raise_for_status()
            results = response.json().get("results", [])
        except (httpx.HTTPError, ValueError, AttributeError) as exc:
            raise ExternalProviderError("Evidence search is temporarily unavailable.") from exc

        evidence: list[EvidenceItem] = []
        for item in results[:5]:
            if not isinstance(item, dict):
                continue
            url = item.get("url", "")
            snippet = item.get("content", "")
            if not isinstance(url, str) or not url.startswith(("https://", "http://")):
                continue
            if not isinstance(snippet, str) or not snippet.strip():
                continue
            raw_score = item.get("score", 0)
            score = raw_score if isinstance(raw_score, (int, float)) else 0
            evidence.append(
                EvidenceItem(
                    source=str(item.get("title") or url)[:300],
                    snippet=snippet[:1200],
                    url=url[:2000],
                    published_at=item.get("published_date"),
                    relevance_score=max(0, min(1, score)),
                )
            )
        return evidence

    @staticmethod
    def _payload(claim: str) -> dict[str, object]:
        return {
            "query": claim,
            "topic": os.getenv("TAVILY_TOPIC", "general"),
            "search_depth": "basic",
            "max_results": 5,
            "include_answer": False,
            "include_published_date": True,
        }
