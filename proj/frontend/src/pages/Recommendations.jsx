import { useMemo, useState } from "react";
import Header from "../components/layout/Header";
import { useLayout } from "../context/LayoutContext";
import Card from "../components/ui/Card";
import LoadingState from "../components/ui/LoadingState";
import ErrorState from "../components/ui/ErrorState";
import RecommendationList from "../components/recommendations/RecommendationList";
import { useFetch } from "../hooks/useFetch";
import { api } from "../services/api";

const PRIORITY_FILTERS = ["All", "CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"];

export default function Recommendations() {
  const { setSidebarOpen } = useLayout();
  const [filter, setFilter] = useState("All");
  const { data, loading, error, refetch } = useFetch(() => api.getRecommendations(), []);

  // Filtering only among priorities the BACKEND actually returned -
  // never invented priority logic in the frontend.
  const availablePriorities = useMemo(
    () => new Set((data?.recommendations ?? []).map((r) => r.priority)),
    [data]
  );
  const filtered = useMemo(() => {
    if (!data) return [];
    if (filter === "All") return data.recommendations;
    return data.recommendations.filter((r) => r.priority === filter);
  }, [data, filter]);

  return (
    <div className="flex-1 overflow-y-auto">
      <Header onMenuClick={() => setSidebarOpen(true)} title="AI Recommendations" subtitle="Rule-based, explainable maintenance and energy-management suggestions." />

      <div className="space-y-6 p-8">
        <Card
          title={`Recommendations (${filtered.length})`}
          action={
            <div className="flex gap-1.5">
              {PRIORITY_FILTERS.filter((p) => p === "All" || availablePriorities.has(p)).map((p) => (
                <button
                  key={p}
                  onClick={() => setFilter(p)}
                  className={`border px-2.5 py-1 text-xs transition ${
                    filter === p
                      ? "border-cyan-600 bg-cyan-500/10 text-cyan-300"
                      : "border-slate-700 text-slate-400 hover:border-slate-600"
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          }
        >
          {loading && <LoadingState label="Loading recommendations..." />}
          {error && <ErrorState message="Unable to load recommendations." onRetry={refetch} />}
          {data && !loading && <RecommendationList recommendations={filtered} />}
        </Card>
      </div>
    </div>
  );
}
