import { useState } from "react";
import Header from "../components/layout/Header";
import { useLayout } from "../context/LayoutContext";
import Card from "../components/ui/Card";
import LoadingState from "../components/ui/LoadingState";
import ErrorState from "../components/ui/ErrorState";
import EnergyHistoryChart from "../components/charts/EnergyHistoryChart";
import EnergyForecastChart from "../components/charts/EnergyForecastChart";
import { useFetch } from "../hooks/useFetch";
import { useEnergyScenario } from "../hooks/useEnergyScenario";
import { api, ApiError } from "../services/api";
import { formatNumber, formatTimestamp } from "../utils/format";
import EnergyScenarioForm from "../components/energy-simulator/EnergyScenarioForm";
import EnergyScenarioResult from "../components/energy-simulator/EnergyScenarioResult";

// Real, achievable ranges only - "7D" is not offered because the
// backend's documented max history limit (1000 records) covers ~6.9
// days at this dataset's 10-minute interval, not a full 7 days.
const RANGE_OPTIONS = [
  { label: "24H", limit: 144 },
  { label: "3D", limit: 432 },
  { label: "Max (1000 records)", limit: 1000 },
];

export default function EnergyIntelligence() {
  const { setSidebarOpen } = useLayout();
  const [rangeLimit, setRangeLimit] = useState(144);
  const [showZones, setShowZones] = useState(true);
  const [horizon, setHorizon] = useState(6);

  const { data: summary, loading: summaryLoading, error: summaryError, refetch: refetchSummary } =
    useFetch(() => api.getEnergySummary(), []);
  const { data: history, loading: historyLoading, error: historyError, refetch: refetchHistory } =
    useFetch(() => api.getEnergyHistory({ limit: rangeLimit }), [rangeLimit]);
  const { data: forecast, loading: forecastLoading, error: forecastError, refetch: refetchForecast } =
    useFetch(() => api.getEnergyForecast(horizon), [horizon]);

  const scenario = useEnergyScenario();

  return (
    <div className="flex-1 overflow-y-auto">
      <Header onMenuClick={() => setSidebarOpen(true)} title="Energy Intelligence" subtitle="Forecasting and historical analysis of public city-level power consumption." />

      <div className="space-y-6 p-8">
        <Card title="Current Energy Snapshot">
          {summaryLoading && <LoadingState label="Loading energy data..." />}
          {summaryError && <ErrorState message="Unable to load energy summary." onRetry={refetchSummary} />}
          {summary && !summaryLoading && (
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
              <div>
                <p className="text-xs text-slate-500">Current</p>
                <p className="mt-1 text-xl font-bold text-slate-100">{formatNumber(summary.current_power, 0)}</p>
                <p className="text-[11px] text-slate-600">{formatTimestamp(summary.current_power_timestamp)}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Recent average ({summary.recent_average_window})</p>
                <p className="mt-1 text-xl font-bold text-slate-100">{formatNumber(summary.recent_average_power, 0)}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">One-step forecast</p>
                <p className="mt-1 text-xl font-bold text-cyan-400">{formatNumber(summary.forecast_power, 0)}</p>
                <p className="text-[11px] text-slate-600">{summary.forecast_horizon}</p>
              </div>
            </div>
          )}
        </Card>

        <Card
          title="Historical Consumption"
          subtitle="Total and per-zone power consumption"
          action={
            <div className="flex items-center gap-2">
              {RANGE_OPTIONS.map((opt) => (
                <button
                  key={opt.label}
                  onClick={() => setRangeLimit(opt.limit)}
                  className={`border px-2.5 py-1 text-xs transition ${
                    rangeLimit === opt.limit
                      ? "border-cyan-600 bg-cyan-500/10 text-cyan-300"
                      : "border-slate-700 text-slate-400 hover:border-slate-600"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
              <label className="ml-2 flex items-center gap-1.5 text-xs text-slate-400">
                <input type="checkbox" checked={showZones} onChange={(e) => setShowZones(e.target.checked)} />
                Show zones
              </label>
            </div>
          }
        >
          {historyLoading && <LoadingState label="Loading energy history..." />}
          {historyError && <ErrorState message="Unable to load energy history." onRetry={refetchHistory} />}
          {history && !historyLoading && <EnergyHistoryChart records={history.records} showZones={showZones} />}
        </Card>

        <Card
          title="Energy Forecast"
          subtitle={forecast ? `Model: ${forecast.model.model_type} - target: ${forecast.target}` : undefined}
          action={
            <select
              value={horizon}
              onChange={(e) => setHorizon(Number(e.target.value))}
              className="border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-slate-300"
            >
              {[3, 6, 12, 18, 36].map((h) => (
                <option key={h} value={h}>{h} steps ({(h * 10)} min)</option>
              ))}
            </select>
          }
        >
          {forecastLoading && <LoadingState label="Loading forecast..." />}
          {forecastError && <ErrorState message="Unable to load forecast." onRetry={refetchForecast} />}
          {forecast && !forecastLoading && (
            <>
              <EnergyForecastChart historyRecords={history?.records?.slice(-48)} forecastPoints={forecast.predictions} />
              <ul className="mt-3 space-y-1 border-t border-slate-800 pt-3">
                {forecast.limitations.map((l, i) => (
                  <li key={i} className="text-[11px] text-slate-500">- {l}</li>
                ))}
              </ul>
            </>
          )}
        </Card>

        <Card
          title="Energy + Production What-If"
          subtitle="Manual scenario: is higher energy consumption proportional to higher production, or a real efficiency concern?"
        >
          <EnergyScenarioForm
            baseline={scenario.baseline}
            scenario={scenario.scenario}
            onBaselineChange={scenario.updateBaseline}
            onScenarioChange={scenario.updateScenario}
            onAnalyze={scenario.analyze}
            onReset={scenario.reset}
            loading={scenario.loading}
          />
          {scenario.error && (
            <div className="mt-4">
              <ErrorState
                message={scenario.error instanceof ApiError ? scenario.error.message : "Unable to analyze scenario."}
                onRetry={scenario.analyze}
              />
            </div>
          )}
          {scenario.loading && <div className="mt-4"><LoadingState label="Analyzing scenario..." /></div>}
          {scenario.result && !scenario.loading && (
            <div className="mt-6 border-t border-slate-800 pt-5">
              <EnergyScenarioResult result={scenario.result} />
            </div>
          )}
          <p className="mt-4 border-t border-slate-800 pt-3 text-[11px] text-slate-600">
            The Tetouan dataset does not include production data - this is a manual what-if layer and does
            not use or modify the trained energy forecasting model.
          </p>
        </Card>

        <Card title="Data Context">
          <div className="text-xs text-slate-400 space-y-1.5">
            <p><span className="text-slate-300">Dataset:</span> UCI Tetouan City Power Consumption</p>
            <p><span className="text-slate-300">Granularity:</span> 10-minute intervals</p>
            <p><span className="text-slate-300">Scope:</span> City-level power consumption</p>
            <p className="pt-1 text-slate-500">
              This dataset is used for energy-intelligence demonstration and does not represent live
              industrial machine energy consumption.
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
}
