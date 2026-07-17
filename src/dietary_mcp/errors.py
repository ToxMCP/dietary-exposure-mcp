from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DietaryErrorPayload(BaseModel):
    code: str = Field(description="Stable machine-readable error code.")
    message: str = Field(description="Human-readable error message.")
    suggestion: str | None = Field(default=None, description="Suggested next action.")
    details: dict[str, Any] = Field(default_factory=dict, description="Structured diagnostics.")


class DietaryError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        suggestion: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.payload = DietaryErrorPayload(
            code=code,
            message=message,
            suggestion=suggestion,
            details=details or {},
        )


class DietaryValidationError(DietaryError):
    pass


class DietaryRegistryError(DietaryError):
    pass
