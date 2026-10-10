"""Dashboard summary service: combines existing service outputs.
Computes nothing new - pure composition (section 16).
"""

from __future__ import annotations

from backend.app.services import energy_service, machine_service, recommendation_service


def _machines_summary() -> dict:
    scored = machine_service.get_scored_anomaly_df()
    counts = scored["anomaly_status"].value_counts().to_dict()

    latest_idx = machine_service._latest_cycle_index()
    latest_row = scored[scored["cycle_index"] == latest_idx].iloc[0]

    return {
        "status_counts": {
            "total": int(len(scored)),
            "normal": int(counts.get("NORMAL", 0)),
            "warning": int(counts.get("WARNING", 0)),
            "anomaly": int(counts.get("ANOMALY", 0)),
        },
        "latest_cycle_index": int(latest_idx),
        "latest_status": str(latest_row["anomaly_status"]),
    }


def get_summary() -> dict:
    energy = energy_service.get_summary()
    machines = _machines_summary()

    rec_result = recommendation_service.get_latest()
    # Top recommendations = highest-priority first, capped to a small
    # dashboard-friendly count (not the full list).
    from ml.recommendation.schemas import PRIORITY_RANK
    recs_sorted = sorted(
        rec_result["recommendations"], key=lambda r: PRIORITY_RANK[r["priority"]], reverse=True
    )

    return {
        "energy": energy,
        "machines": machines,
        "top_recommendations": recs_sorted[:5],
    }
