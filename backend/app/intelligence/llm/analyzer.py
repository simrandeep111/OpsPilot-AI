import json
from dataclasses import dataclass

import httpx

from app.intelligence.llm.prompts import (
    SYSTEM_PROMPT,
    incident_prompt,
)
from app.models.metric import MetricSnapshot


@dataclass(frozen=True)
class Analysis:
    likely_cause: str
    recommended_action: str
    source: str
    affected_resources: list[str]


class AIAnalyzer:
    def __init__(
        self,
        provider: str | None,
        api_key: str | None,
        model: str | None,
        client: httpx.AsyncClient | None = None,
    ):
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.client = client

    @property
    def configured(self) -> bool:
        return bool(self.provider and self.api_key and self.model)

    async def test_and_configure(self, provider: str, api_key: str, model: str) -> None:
        if provider == "openai":
            payload = {"model": model, "input": "Reply with OK.", "max_output_tokens": 8}
        elif provider == "anthropic":
            payload = {
                "model": model,
                "max_tokens": 8,
                "messages": [{"role": "user", "content": "Reply with OK."}],
            }
        else:
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": "Reply with OK."}],
                "max_completion_tokens": 8,
            }
        response = await self._post(provider, payload, api_key)
        response.raise_for_status()
        self.provider = provider
        self.api_key = api_key
        self.model = model

    async def _post(self, provider: str, payload: dict, api_key: str):
        if provider == "openai":
            url = "https://api.openai.com/v1/responses"
            headers = {"Authorization": f"Bearer {api_key}"}
        elif provider == "anthropic":
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            }
        else:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}"}
        if self.client:
            return await self.client.post(url, json=payload, headers=headers)
        async with httpx.AsyncClient(timeout=45) as client:
            return await client.post(url, json=payload, headers=headers)

    @staticmethod
    def _text(provider: str, payload: dict) -> str:
        if provider == "openai":
            if payload.get("output_text"):
                return payload["output_text"]
            return "".join(
                content.get("text", "")
                for item in payload.get("output", [])
                for content in item.get("content", [])
                if content.get("type") == "output_text"
            )
        if provider == "anthropic":
            return "".join(
                content.get("text", "")
                for content in payload.get("content", [])
                if content.get("type") == "text"
            )
        return payload["choices"][0]["message"]["content"]

    async def analyze(
        self,
        metrics: MetricSnapshot,
        problem_type: str,
        severity: str,
        source_context: dict | None = None,
    ) -> Analysis:
        if not self.configured:
            return Analysis(
                likely_cause=f"Metrics indicate {problem_type.replace('_', ' ')}.",
                recommended_action="Inspect the affected resource and its recent changes.",
                source="fallback (AI provider not configured)",
                affected_resources=[],
            )

        prompt = incident_prompt(
            metrics.as_context(),
            problem_type,
            severity,
            json.dumps(source_context or {}, default=str)[:20000],
        )
        if self.provider == "openai":
            payload = {
                "model": self.model,
                "input": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "max_output_tokens": 1200,
            }
        elif self.provider == "anthropic":
            payload = {
                "model": self.model,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1200,
            }
        else:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "response_format": {"type": "json_object"},
            }
        response = await self._post(self.provider, payload, self.api_key)
        response.raise_for_status()
        text = self._text(self.provider, response.json())
        parsed = json.loads(text[text.find("{"):text.rfind("}") + 1])
        return Analysis(
            likely_cause=str(parsed["likely_cause"]),
            recommended_action=str(parsed["recommended_action"]),
            source=f"{self.provider}:{self.model}",
            affected_resources=[str(resource) for resource in parsed.get("affected_resources", [])],
        )
