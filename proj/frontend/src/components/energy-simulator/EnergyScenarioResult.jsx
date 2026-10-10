import { CheckCircle2, AlertTriangle } from "lucide-react";
import { formatNumber } from "../../utils/format";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts";

function ChangeStat({ label, value, unit = "%" }) {
  const positive = value > 0;
  const color = value === 0 ? "text-slate-300" : positive ? "text-amber-300" : "text-emerald-400";
  return (
    <div>
      <p className="text-xs text-slate-500">{label}</p>
      <p className={`mt-1 text-xl font-bold ${color}`}>
        {value > 0 ? "+" : ""}{formatNumber(value, 1)}{unit}
      </p>
    </div>
  );
}

function IntensityBarChart({ baseline, scenario }) {
  const data = [
    { name: "Baseline", value: baseline.energy_intensity },
    { name: "Scenario", value: scenario.energy_intensity },
  ];
  return (
    <ResponsiveContainer width="100%" height={120}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 24, left: 8, bottom: 4 }}>
        <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" stroke="#64748b" fontSize={11} tickLine={false} />
        <YAxis type="category" dataKey="name" stroke="#94a3b8" fontSize={11} width={64} tickLine={false} />
        <Tooltip
          contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", fontSize: 12 }}
          formatter={(v) => [`${v.toFixed(2)} kWh/unit`, "Energy intensity"]}
        />
        <Bar dataKey="value" isAnimationActive={false} radius={[0, 2, 2, 0]} fill="#22d3ee" />
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Real API result only - status/classification/explanation/numbers
 * all come straight from the backend's response, nothing computed or
 * invented here. */
export default function EnergyScenarioResult({ result }) {
  if (!result) return null;
  const isWarning = result.status === "WARNING";

  return (
    <div>
      <div className="mb-3 flex items-center gap-2">
        <span className="border border-amber-700 bg-amber-500/10 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-amber-400">
          Simulated Scenario
        </span>
        <span className="text-xs text-slate-500">manual what-if, not historical production data</span>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <ChangeStat label="Production Change" value={result.changes.production_percent} />
        <ChangeStat label="Energy Change" value={result.changes.energy_percent} />
        <ChangeStat label="Energy Intensity Change" value={result.changes.energy_intensity_percent} />
        <div>
          <p className="text-xs text-slate-500">Energy Intensity</p>
          <p className="mt-1 text-xl font-bold text-slate-100">
            {formatNumber(result.baseline.energy_intensity, 2)} → {formatNumber(result.scenario.energy_intensity, 2)}
          </p>
          <p className="text-[11px] text-slate-600">kWh/unit</p>
        </div>
      </div>

      <div className="mt-5">
        <IntensityBarChart baseline={result.baseline} scenario={result.scenario} />
      </div>

      <div className={`mt-5 flex items-start gap-3 border px-4 py-3 ${
        isWarning ? "border-amber-700/50 bg-amber-950/20" : "border-emerald-700/50 bg-emerald-950/20"
      }`}>
        {isWarning ? (
          <AlertTriangle size={18} className="mt-0.5 shrink-0 text-amber-400" />
        ) : (
          <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-emerald-400" />
        )}
        <div>
          <p className={`text-sm font-semibold ${isWarning ? "text-amber-300" : "text-emerald-300"}`}>
            {isWarning ? "ENERGY EFFICIENCY WARNING" : "NORMAL / PROPORTIONAL"}
          </p>
          <p className="mt-1 text-sm text-slate-400">{result.explanation}</p>
        </div>
      </div>

      <p className="mt-3 text-[11px] text-slate-600">
        Threshold: {result.threshold_percent}% - {result.threshold_note}
      </p>
      <p className="mt-1 text-[11px] text-slate-600">{result.note}</p>
    </div>
  );
}
