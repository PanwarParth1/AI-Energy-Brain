"""Top-level Recommendation Engine (sections 3, 10, 16, 19).

generate_recommendations() is the single entry point: it accepts
whichever signals are available (machine health/anomaly for one cycle,
and/or one energy observation), builds per-track recommendations via
machine_rules.py / energy_rules.py, and applies cross-track logic when
both tracks are present.

CROSS-TRACK HONESTY NOTE (read before using the combined path):
The Tetouan energy dataset (Morocco, 2017) and the hydraulic dataset
(ZeMA test rig) are two independent, unrelated real datasets with no
shared timeline or facility. There is no genuine "machine's energy use
at this instant" signal in this project. When both tracks are supplied
together, this is DECLARED here and in every combined recommendation's
limitations - it demonstrates the engine's cross-track LOGIC using two
real, independently-sourced observations, not a real correlated event.
A future unified deployment (with both signals from the same real
facility) would remove this caveat.
"""

from __future__ import annotations

from ml.recommendation.energy_rules import build_energy_recommendation
from ml.recommendation.machine_rules import build_machine_recommendation
from ml.recommendation.schemas import CATEGORIES, Evidence, Recommendation, escalate, max_priority


def _dedupe(recs: list[Recommendation]) -> list[Recommendation]:
    """Drop exact duplicate (category, priority, title) recommendations.
    Consolidation of MULTIPLE evidence into ONE recommendation already
    happens inside machine_rules/energy_rules (section 16); this is a
    final safety net against literal duplicates, not the primary
    mechanism.
    """
    seen = set()
    out = []
    for r in recs:
        key = (r.category, r.priority, r.title)
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def generate_recommendations(
    health_result: dict | None = None,
    anomaly_result: dict | None = None,
    cycle_index: int | None = None,
    energy_observation: dict | None = None,
) -> list[Recommendation]:
    """Build the full recommendation list for one evaluation context.

    health_result / anomaly_result / cycle_index: machine track, as
        produced by ml.machine_health.predict.predict_from_sensors()
        (as a dict) and ml.machine_health.anomaly.detect_anomaly().
        Any of these may be None (TEST 8: graceful degradation).
    energy_observation: energy track, as produced by
        ml.recommendation.energy_rules.get_recent_energy_observation()
        - {"datetime", "actual", "trailing_mean"}. May be None.

    Returns a deduplicated list of Recommendation objects. An empty
    list means "nothing rose above NO_ACTION on any track" (Case E).
    """
    recs: list[Recommendation] = []

    machine_rec = None
    if health_result is not None or anomaly_result is not None:
        machine_rec = build_machine_recommendation(
            health_result=health_result,
            anomaly_result=anomaly_result,
            cycle_index=cycle_index,
            rec_index=0,
        )
        if machine_rec is not None:
            recs.append(machine_rec)

    energy_rec = None
    if energy_observation is not None:
        energy_rec = build_energy_recommendation(
            datetime_value=energy_observation["datetime"],
            actual=energy_observation["actual"],
            trailing_mean=energy_observation["trailing_mean"],
            rec_index=0,
        )
        if energy_rec is not None:
            recs.append(energy_rec)

    # --- cross-track logic (section 19) ---------------------------------
    if machine_rec is not None and energy_rec is not None:
        from ml.recommendation.schemas import PRIORITY_RANK
        if PRIORITY_RANK[machine_rec.priority] >= PRIORITY_RANK["MEDIUM"] and \
           PRIORITY_RANK[energy_rec.priority] >= PRIORITY_RANK["MEDIUM"]:

            combined_priority = max_priority(machine_rec.priority, energy_rec.priority)
            if machine_rec.priority == "HIGH" and energy_rec.priority == "HIGH":
                combined_priority = escalate(combined_priority, 1)  # documented single-step escalation

            import datetime as _dt
            cross_rec = Recommendation(
                recommendation_id=f"REC-CROSS-{cycle_index if cycle_index is not None else 'NA'}",
                category="MACHINE_INSPECTION",
                priority=combined_priority,
                title="Coinciding abnormal machine and energy signals",
                action="Investigate the machine's operating condition and the concurrent elevated energy demand together.",
                reason=("Both the machine track and the energy track independently indicate abnormal "
                        "behaviour. Coinciding abnormal machine and energy signals warrant investigation; "
                        "this does not establish that one caused the other."),
                evidence=[
                    Evidence(signal="machine_track", observation=machine_rec.title, severity="high", source="machine_rules"),
                    Evidence(signal="energy_track", observation=energy_rec.title, severity="high", source="energy_rules"),
                ],
                confidence=min(1.0, 0.5 * (machine_rec.confidence + energy_rec.confidence)),
                confidence_basis="Rule confidence combining both tracks' individual rule confidences. NOT a statistical probability.",
                machine_id=machine_rec.machine_id,
                cycle_index=cycle_index,
                energy_datetime=energy_rec.energy_datetime,
                source_models=list(set(machine_rec.source_models + energy_rec.source_models)),
                limitations=machine_rec.limitations + energy_rec.limitations + [
                    "CROSS-TRACK CAVEAT: the machine (hydraulic test rig) and energy "
                    "(Tetouan city) datasets are independent and do not share a real "
                    "timeline or facility. This combined recommendation demonstrates "
                    "the engine's cross-track logic using two real but unrelated "
                    "observations, not a genuine correlated event.",
                ],
                generated_at=_dt.datetime.now().isoformat(timespec="seconds"),
            )
            recs.append(cross_rec)

    # --- Case E: nothing flagged on either track -----------------------
    if not recs:
        import datetime as _dt
        recs.append(Recommendation(
            recommendation_id=f"REC-MONITOR-{cycle_index if cycle_index is not None else 'NA'}",
            category="CONTINUE_MONITORING",
            priority="INFO",
            title="Machine and/or energy behaviour within reference range",
            action="Continue normal monitoring.",
            reason="No significant anomaly, degraded-condition, or elevated-energy signal detected.",
            evidence=[],
            confidence=1.0,
            confidence_basis="No supporting evidence was found for an elevated recommendation; this is the deterministic default state.",
            machine_id="hydraulic_test_rig",
            cycle_index=cycle_index,
            energy_datetime=energy_observation["datetime"].isoformat() if energy_observation else None,
            source_models=[],
            limitations=["This is decision support only and does not replace qualified maintenance or engineering inspection."],
            generated_at=_dt.datetime.now().isoformat(timespec="seconds"),
        ))

    return _dedupe(recs)
