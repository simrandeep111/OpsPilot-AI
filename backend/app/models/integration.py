from typing import Literal

from pydantic import BaseModel, Field


class AIConnection(BaseModel):
    provider: Literal["openai", "anthropic", "groq"]
    api_key: str = Field(min_length=10)
    model: str = Field(min_length=1)


class DecisionModelConnection(BaseModel):
    provider: Literal["openrouter"]
    api_key: str = Field(min_length=10)
    model: Literal["~typesafe/jev-latest", "typesafe/jev-1.13"]


class AWSConnection(BaseModel):
    role_arn: str = Field(pattern=r"^arn:aws:iam::\d{12}:role/.+$")
    external_id: str = Field(min_length=2)
    regions: list[str] = Field(min_length=1)


class SlackConnection(BaseModel):
    webhook_url: str = Field(
        pattern=r"^https://hooks\.(slack\.com|slack-gov\.com)/services/.+$"
    )
