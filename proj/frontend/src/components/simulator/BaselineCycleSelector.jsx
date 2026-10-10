import { useState } from "react";
import { RefreshCw } from "lucide-react";

export default function BaselineCycleSelector({ maxCycleIndex, currentCycleIndex, onLoad, loading }) {
  const [input, setInput] = useState(String(currentCycleIndex ?? ""));

  function handleLoad() {
    const idx = parseInt(input, 10);
    if (!Number.isNaN(idx) && idx >= 0 && idx <= maxCycleIndex) {
      onLoad(idx);
    }
  }

  return (
    <div>
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <label htmlFor="baseline-cycle-input" className="mb-1 block text-xs text-slate-500">
            Baseline cycle (0-{maxCycleIndex})
          </label>
          <input
            id="baseline-cycle-input"
            type="number"
            min={0}
            max={maxCycleIndex}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleLoad()}
            disabled={loading}
            className="w-40 border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-500 disabled:opacity-50"
          />
        </div>
        <button
          onClick={handleLoad}
          disabled={loading}
          className="flex items-center gap-2 border border-slate-700 px-3 py-2 text-sm text-slate-300 transition hover:border-slate-500 disabled:opacity-50"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          {loading ? "Loading..." : "Load Baseline"}
        </button>
      </div>
      <p className="mt-2 text-xs text-slate-600">
        Currently loaded: cycle {currentCycleIndex ?? "-"} (real data from the hydraulic test rig)
      </p>
    </div>
  );
}
