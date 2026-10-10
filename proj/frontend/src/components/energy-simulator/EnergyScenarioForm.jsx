import { Play, RotateCcw } from "lucide-react";
import { formatNumber } from "../../utils/format";

function NumberField({ label, value, onChange, unit, disabled }) {
  return (
    <div>
      <label className="mb-1 block text-xs text-slate-500">{label}</label>
      <div className="flex items-center gap-2">
        <input
          type="number"
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          disabled={disabled}
          className="w-full border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-500 disabled:opacity-50"
        />
        <span className="shrink-0 text-xs text-slate-500">{unit}</span>
      </div>
    </div>
  );
}

function IntensityPreview(point) {
  const intensity = point.production > 0 ? point.energy / point.production : null;
  return (
    <p className="mt-2 text-xs text-slate-500">
      Energy intensity (preview):{" "}
      <span className="font-medium text-slate-300">
        {intensity != null ? formatNumber(intensity, 2) : "—"} kWh/unit
      </span>
    </p>
  );
}

/** Manual production + energy inputs only - the Tetouan dataset has no
 * production data (see Part 14 README section) - and a client-side
 * division PREVIEW, never the authoritative classification. */
export default function EnergyScenarioForm({ baseline, scenario, onBaselineChange, onScenarioChange, onAnalyze, onReset, loading }) {
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <div className="border border-slate-800 bg-slate-950/40 p-4">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">Baseline</p>
        <div className="space-y-3">
          <NumberField label="Production Output" unit="units" value={baseline.production}
            onChange={(v) => onBaselineChange({ production: v })} disabled={loading} />
          <NumberField label="Energy Consumption" unit="kWh" value={baseline.energy}
            onChange={(v) => onBaselineChange({ energy: v })} disabled={loading} />
        </div>
        <IntensityPreview {...baseline} />
      </div>

      <div className="border border-amber-900/40 bg-amber-950/10 p-4">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-amber-500">Simulated Scenario</p>
        <div className="space-y-3">
          <NumberField label="Production Output" unit="units" value={scenario.production}
            onChange={(v) => onScenarioChange({ production: v })} disabled={loading} />
          <NumberField label="Energy Consumption" unit="kWh" value={scenario.energy}
            onChange={(v) => onScenarioChange({ energy: v })} disabled={loading} />
        </div>
        <IntensityPreview {...scenario} />
      </div>

      <div className="lg:col-span-2 flex items-center gap-3 border-t border-slate-800 pt-4">
        <button
          onClick={onAnalyze}
          disabled={loading}
          className="flex items-center gap-2 border border-cyan-700 bg-cyan-500/10 px-5 py-2.5 text-sm font-semibold text-cyan-300 transition hover:bg-cyan-500/20 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Play size={14} />
          {loading ? "Analyzing scenario..." : "ANALYZE SCENARIO"}
        </button>
        <button
          onClick={onReset}
          disabled={loading}
          className="flex items-center gap-2 border border-slate-700 px-4 py-2.5 text-sm text-slate-400 transition hover:border-slate-500 hover:text-slate-200 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <RotateCcw size={14} />
          RESET SCENARIO
        </button>
      </div>
    </div>
  );
}
