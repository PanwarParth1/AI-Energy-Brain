"""Structured schemas for the Recommendation Engine (Part 9).

Plain dataclasses/dicts, not a new ML model - the engine itself is
deterministic rule-based logic, per the Part 9 spec.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

# --- Categories (section 5) --------------------------------------------
CATEGORIES = [
    "MACHINE_INSPECTION",
    "PREVENTIVE_MAINTENANCE",
    "ENERGY_MONITORING",
    "ENERGY_OPTIMIZATION",
    "CONTINUE_MONITORING",
    "NO_ACTION",
]

# --- Priorities (section 6), ordered low -> high ------------------------
PRIORITIES = ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
PRIORITY_RANK = {p: i for i, p in enumerate(PRIORITIES)}


def max_priority(a: str, b: str) -> str:
    return a if PRIORITY_RANK[a] >= PRIORITY_RANK[b] else b


def escalate(priority: str, levels: int = 1) -> str:
    """Move a priority up by `levels` steps, capped at CRITICAL."""
    idx = min(PRIORITY_RANK[priority] + levels, len(PRIORITIES) - 1)
    return PRIORITIES[idx]


@dataclass
class Evidence:
    """One structured piece of supporting evidence (section 11)."""
    signal: str        # e.g. "vibration", "anomaly_score", "energy_forecast"
    observation: str    # e.g. "above_reference", "high", "elevated_vs_recent"
    severity: str        # "low" | "moderate" | "high"
    source: str          # which model/module produced this signal

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Recommendation:
    """One structured recommendation (section 12)."""
    recommendation_id: str
    category: str
    priority: str
    title: str
    action: str
    reason: str
    evidence: list[Evidence]
    confidence: float
    confidence_basis: str  # what "confidence" means for THIS recommendation
    machine_id: str
    cycle_index: int | None
    energy_datetime: str | None
    source_models: list[str]
    limitations: list[str]
    generated_at: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d["evidence"] = [e.to_dict() if isinstance(e, Evidence) else e for e in self.evidence]
        return d

    def __post_init__(self):
        assert self.category in CATEGORIES, f"Unknown category: {self.category}"
        assert self.priority in PRIORITIES, f"Unknown priority: {self.priority}"
        assert 0.0 <= self.confidence <= 1.0, f"confidence out of range: {self.confidence}"
