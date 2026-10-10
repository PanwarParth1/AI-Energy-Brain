"""Alert service: derives alerts from EXISTING anomaly + recommendation
outputs (section 15) - explicitly not a second, separate alerting
system. An "alert" here is just a status/event view; a "recommendation"
(from recommendation_service) is the corresponding suggested action.
"""

from __future__ import annotations

from backend.app.core.config import settings
from backend.app.services import machine_service, recommendation_service


def get_alerts() -> dict:
    alerts = []

    latest_idx = machine_service._latest_cycle_index()
    anomaly = machine_service.get_anomaly(settings.MACHINE_ID, latest_idx)

    if anomaly["status"] != "NORMAL":
        alerts.append({
            "alert_id": f"ALERT-ANOMALY-{latest_idx}",
            "severity": anomaly["status"],
            "category": "machine_anomaly",
            "title": f"Anomaly status {anomaly['status']} on latest cycle",
            "machine_id": anomaly["machine_id"],
            "cycle_index": latest_idx,
            "source": "machine_anomaly_detector",
        })

    rec_result = recommendation_service.get_latest()
    for rec in rec_result["recommendations"]:
        if rec["priority"] in ("HIGH", "CRITICAL"):
            alerts.append({
                "alert_id": rec["recommendation_id"].replace("REC-", "ALERT-"),
                "severity": rec["priority"],
                "category": "recommendation",
                "title": rec["title"],
                "machine_id": rec["machine_id"],
                "cycle_index": rec["cycle_index"],
                "source": "recommendation_engine",
            })

    return {"count": len(alerts), "alerts": alerts}
