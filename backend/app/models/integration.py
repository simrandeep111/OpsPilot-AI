from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, Field, model_validator


class AIConnection(BaseModel):
    provider: Literal["openai", "anthropic", "groq"]
    api_key: str = Field(min_length=10)
    model: str = Field(min_length=1)


class DecisionModelConnection(BaseModel):
    provider: Literal["openrouter"]
    api_key: str = Field(min_length=10)
    model: Literal["~typesafe/jev-latest", "typesafe/jev-1.13"]


class PrometheusConnection(BaseModel):
    url: AnyHttpUrl
    auth_type: Literal["none", "basic", "bearer"] = "none"
    username: str | None = Field(default=None, min_length=1)
    password: str | None = Field(default=None, min_length=1)
    token: str | None = Field(default=None, min_length=1)
    service_name: str = Field(default="prometheus", min_length=1, pattern=r"^[a-zA-Z0-9_.:/-]+$")

    @model_validator(mode="after")
    def validate_auth(self):
        if self.url.username or self.url.password:
            raise ValueError("Put credentials in the authentication fields, not the URL")
        if self.auth_type == "basic" and not (self.username and self.password):
            raise ValueError("Username and password are required for Basic Auth")
        if self.auth_type == "bearer" and not self.token:
            raise ValueError("Token is required for Bearer authentication")
        return self


class SlackConnection(BaseModel):
    webhook_url: str = Field(
        pattern=r"^https://hooks\.(slack\.com|slack-gov\.com)/services/.+$"
    )
