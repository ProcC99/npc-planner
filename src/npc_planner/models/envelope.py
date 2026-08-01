from typing import Any

from pydantic import BaseModel, Field


class ExcludedReason(BaseModel):
    key: str
    reasons: list[dict[str, Any]] | list[str]


class Meta(BaseModel):
    count: int = 0
    elapsed_ms: float = 0.0
    deterministic_hash: str | None = None


class Envelope[T](BaseModel):
    query: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    results: T
    excluded: list[ExcludedReason] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    meta: Meta = Field(default_factory=Meta)
