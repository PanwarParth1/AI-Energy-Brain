import { formatNumber } from "../../utils/format";

/** Real before/after numbers straight from the API's `changes` field -
 * nothing computed or invented here. */
export default function ScenarioChangesSummary({ changes }) {
  if (!changes || Object.keys(changes).length === 0) return null;

  return (
    <div className="space-y-2">
      {Object.entries(changes).map(([sensor, c]) => {
        const delta = c.simulated_mean - c.baseline_mean;
        const pct = c.baseline_mean !== 0 ? (delta / c.baseline_mean) * 100 : null;
        return (
          <div key={sensor} className="flex items-center justify-between border border-slate-800 bg-slate-950/40 px-4 py-2.5 text-sm">
            <div>
              <span className="font-medium text-slate-200">{sensor}</span>
              <span className="ml-2 text-xs text-slate-500">
                {c.mode} {c.mode === "multiply" ? `${c.value}×` : (c.value > 0 ? `+${c.value}` : c.value)}
              </span>
            </div>
            <div className="text-right">
              <span className="text-slate-400">{formatNumber(c.baseline_mean, 2)}</span>
              <span className="mx-2 text-slate-600">→</span>
              <span className="font-medium text-amber-300">{formatNumber(c.simulated_mean, 2)}</span>
              <span className="ml-2 text-xs text-slate-500">{c.unit}</span>
              {pct != null && (
                <span className="ml-2 text-xs text-slate-600">
                  ({delta >= 0 ? "+" : ""}{formatNumber(pct, 0)}%)
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
