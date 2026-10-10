import Badge from "../ui/Badge";
import { formatNumber } from "../../utils/format";

/** health: the actual /machines/{id}/health response shape:
 * {predicted_condition, predicted_condition_meaning, confidence, class_probabilities, ...} */
export default function MachineHealthCard({ health }) {
  if (!health) return null;

  // Semantic tone from the meaning text itself (documented UCI wording),
  // never a hardcoded number->color mapping the model didn't provide.
  const meaning = health.predicted_condition_meaning?.toLowerCase() ?? "";
  const tone = meaning.includes("close to total failure")
    ? "CRITICAL"
    : meaning.includes("reduced")
    ? "WARNING"
    : "NORMAL";

  return (
    <div>
      <div className="flex items-baseline gap-3">
        <span className="text-3xl font-bold text-slate-100">{health.predicted_condition}</span>
        <Badge label={health.predicted_condition_meaning} tone={tone} />
      </div>
      <p className="mt-1 text-xs text-slate-500">Cooler condition classification (Part 7)</p>

      <div className="mt-4 flex items-center justify-between text-sm">
        <span className="text-slate-500">Model confidence</span>
        <span className="font-medium text-slate-200">{formatNumber(health.confidence * 100, 1)}%</span>
      </div>

      {health.class_probabilities && (
        <div className="mt-3 space-y-1.5">
          {Object.entries(health.class_probabilities).map(([cls, prob]) => (
            <div key={cls} className="flex items-center gap-2 text-xs">
              <span className="w-8 text-slate-500">{cls}</span>
              <div className="h-1.5 flex-1 bg-slate-800">
                <div className="h-1.5 bg-cyan-500/70" style={{ width: `${prob * 100}%` }} />
              </div>
              <span className="w-10 text-right text-slate-400">{formatNumber(prob * 100, 0)}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
