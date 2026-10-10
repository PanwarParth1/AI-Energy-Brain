"""Shared response pieces used across multiple route modules."""

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class ModelInfo(BaseModel):
    """Minimal, non-sensitive model identity - never exposes file paths."""
    name: str
    model_type: str
    dataset: str
