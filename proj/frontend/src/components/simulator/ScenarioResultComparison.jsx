import { ArrowRight } from "lucide-react";
import Badge from "../ui/Badge";
import SensorDeviationChart from "../charts/SensorDeviationChart";
import { formatNumber } from "../../utils/format";

function ResultPanel({ title, health, anomaly, tone }) {
  return (
    <div className={`flex-1 border p-5 ${tone === "simulated" ? "border-amber-700/50 bg-amber-950/10" : "border-slate-800 bg-slate-900/40"}`}>
      <p className={`text-xs font-semibold uppercase tracking-wide ${tone === "simulated" ? "text-amber-400" : "text-slate-500"}`}>
        {title}
      </p>

      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-2xl font-bold text-slate-100">{health.predicted_condition}</span>
        <span className="text-sm text-slate-400">{health.predicted_condition_meaning}</span>
      </div>
      <p className="mt-1 text-xs text-slate-500">Confidence: {formatNumber(health.confidence * 100, 1)}%</p>

      <div className="mt-4 flex items-center gap-2">
        <Badge label={anomaly.status} />
        <span className="text-xs text-slate-500">score {formatNumber(anomaly.anomaly_score, 3)}</span>
      </div>

      {anomaly.top_deviations?.length > 0 && (
        <div className="mt-4">
          <SensorDeviationChart deviations={anomaly.top_deviations} />
        </div>
      )}
    </div>
  );
}

/** Baseline -> Simulated, side by side, using ONLY real API values. */
export default function ScenarioResultComparison({ result }) {
  if (!result) return null;

  return (
    <div>
      <div className="mb-3 flex items-center gap-2">
        <span className="border border-amber-700 bg-amber-500/10 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-amber-400">
          Simulated Scenario
        </span>
        <span className="text-xs text-slate-500">what-if result, not a live measurement</span>
      </div>

      <div className="flex flex-col items-stretch gap-4 lg:flex-row lg:items-center">
        <ResultPanel title="Baseline" health={result.baseline.health} anomaly={result.baseline.anomaly} tone="baseline" />
        <ArrowRight className="hidden shrink-0 text-slate-600 lg:block" size={28} />
        <ResultPanel title="Simulated" health={result.simulated.health} anomaly={result.simulated.anomaly} tone="simulated" />
      </div>

      <p className="mt-4 border-t border-slate-800 pt-3 text-xs leading-relaxed text-slate-500">{result.note}</p>
    </div>
  );
}
