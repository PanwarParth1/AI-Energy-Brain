"""Machine / Machine-Health API schemas (sections 9, 12).

The hydraulic dataset represents ONE test rig, not a factory fleet -
schemas reflect that (a list of one, not an invented fleet).
"""

from __future__ import annotations

from pydantic import BaseModel


class MachineInfo(BaseModel):
    machine_id: str
    name: str
    source: str
    dataset_type: str
    n_cycles_available: int


class MachineListResponse(BaseModel):
    machines: list[MachineInfo]


class MachineHealthResponse(BaseModel):
    machine_id: str
    cycle_index: int
    predicted_condition: int
    predicted_condition_meaning: str
    confidence: float
    class_probabilities: dict[str, float]
    model_type: str
    dataset: str
    limitations: list[str]
