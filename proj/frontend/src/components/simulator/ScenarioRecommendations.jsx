import { Info } from "lucide-react";
import ErrorState from "../ui/ErrorState";
import EmptyState from "../ui/EmptyState";
import RecommendationCard from "../recommendations/RecommendationCard";

const NO_ACTION_CATEGORIES = ["CONTINUE_MONITORING", "NO_ACTION"];
const PRIORITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"];

/** Describe a recorded sensor change from the real /simulate response, e.g. "VS1 x5" / "TS2 +30 degC". */
function describeChange(sensor, change) {
  const v = Number(change.value);
  return change.mode === "multiply"
    ? `${sensor} x${v}`
    : `${sensor} ${v >= 0 ? "+" : ""}${v} ${change.unit}`;
}

/**
 * Recommendations for ONE analyzed what-if scenario.
 *
 * `result` is the real POST /api/machines/simulate response. The recommendations in it
 * were produced on the backend by the existing Part 9 rule engine from the SIMULATED
 * health + anomaly outputs - nothing is decided or hardcoded here. This component only
 * renders them. It is always given the current `result` (cleared by the hook on every
 * new analysis / reset), so it cannot show a previous scenario's recommendations.
 */
export default function ScenarioRecommendations({ result }) {
  const { recommendations, recommendations_error: error, recommendation_note: note } = result;

  // Error: the simulation itself succeeded, only the recommendation step failed.
  if (error) {
    return <ErrorState message={error} />;
  }

  // Older/unsupported backend response without the field: say so, do not invent anything.
  if (recommendations === undefined || recommendations === null) {
    return <EmptyState message="Recommendations are not available for this scenario." />;
  }

  if (recommendations.length === 0) {
    return <EmptyState message="The recommendation engine returned nothing for this scenario." />;
  }

  const sorted = [...recommendations].sort(
    (a, b) => PRIORITY_ORDER.indexOf(a.priority) - PRIORITY_ORDER.indexOf(b.priority)
  );
  const noActionRequired = sorted.every((r) => NO_ACTION_CATEGORIES.includes(r.category));

  const changed = Object.entries(result.changes ?? {}).map(([s, c]) => describeChange(s, c));
  const sim = result.simulated;

  return (
    <div className="space-y-4">
      <div className="space-y-1 border border-slate-800 bg-slate-950/50 px-4 py-3 text-xs text-slate-400">
        <p>
          <span className="text-slate-500">Evaluated scenario:</span>{" "}
          {changed.length > 0 ? changed.join(", ") : "no sensor changes"} (baseline cycle{" "}
          {result.baseline_cycle_index})
        </p>
        <p>
          <span className="text-slate-500">Simulated outputs used:</span>{" "}
          {sim.health.predicted_condition_meaning} / anomaly status {sim.anomaly.status}
        </p>
      </div>

      {noActionRequired && (
        <p className="border border-emerald-900/50 bg-emerald-950/20 px-4 py-2 text-sm text-emerald-300">
          No action required for this scenario - the engine found no abnormal signal in the simulated results.
        </p>
      )}

      <div className="space-y-3">
        {sorted.map((rec, i) => (
          <RecommendationCard
            key={`${rec.recommendation_id}-${i}`}
            rec={rec}
            contextLabel={`Simulated scenario (baseline cycle ${result.baseline_cycle_index})`}
          />
        ))}
      </div>

      {note && (
        <div className="flex items-start gap-3 text-xs text-slate-500">
          <Info size={14} className="mt-0.5 shrink-0 text-slate-600" />
          <p>{note}</p>
        </div>
      )}
    </div>
  );
}
