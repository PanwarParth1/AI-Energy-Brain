import { useState } from "react";
import { Search } from "lucide-react";
import { api, ApiError } from "../../services/api";
import LoadingState from "../ui/LoadingState";
import ErrorState from "../ui/ErrorState";
import MachineHealthCard from "./MachineHealthCard";
import AnomalyCard from "./AnomalyCard";
import RecommendationList from "../recommendations/RecommendationList";
import Card from "../ui/Card";

/** The primary demo interaction: enter a cycle index, run it through
 * the real Part 7 + 8 + 9 pipeline via POST /api/machines/analyze,
 * and render the actual response. No ML logic here - just display. */
export default function CycleAnalyzer({ maxCycleIndex }) {
  const [cycleInput, setCycleInput] = useState("301");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleAnalyze() {
    const cycleIndex = parseInt(cycleInput, 10);
    if (Number.isNaN(cycleIndex)) {
      setError(new ApiError("BAD_REQUEST", "Enter a whole number cycle index."));
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await api.analyzeMachine(cycleIndex);
      setResult(data);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="flex items-end gap-3">
        <div>
          <label htmlFor="cycle-index-input" className="mb-1 block text-xs text-slate-500">
            Cycle index {maxCycleIndex != null ? `(0-${maxCycleIndex})` : ""}
          </label>
          <input
            id="cycle-index-input"
            type="number"
            min={0}
            max={maxCycleIndex ?? undefined}
            value={cycleInput}
            onChange={(e) => setCycleInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAnalyze()}
            className="w-40 border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-500"
          />
        </div>
        <button
          onClick={handleAnalyze}
          disabled={loading}
          className="flex items-center gap-2 border border-cyan-700 bg-cyan-500/10 px-4 py-2 text-sm font-medium text-cyan-300 transition hover:bg-cyan-500/20 disabled:opacity-50"
        >
          <Search size={14} />
          {loading ? "Analyzing..." : "Analyze Cycle"}
        </button>
      </div>

      <div className="mt-6">
        {loading && <LoadingState label="Analyzing sensor state..." />}
        {error && (
          <ErrorState
            message={error instanceof ApiError ? error.message : "Unable to load machine analysis."}
            onRetry={handleAnalyze}
          />
        )}

        {result && !loading && !error && (
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
            <Card title="Machine Health" subtitle="Part 7 classification">
              <MachineHealthCard health={result.health} />
            </Card>
            <Card title="Anomaly Detection" subtitle="Part 8 detector">
              <AnomalyCard anomaly={result.anomaly} />
            </Card>
            <Card title="AI Recommendations" subtitle="Part 9 rule engine">
              <RecommendationList recommendations={result.recommendations} />
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
