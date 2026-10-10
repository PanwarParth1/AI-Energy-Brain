"""Pydantic response models for system endpoints.

Declaring the shape here means FastAPI validates what we send and
documents it automatically at /docs.
"""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
