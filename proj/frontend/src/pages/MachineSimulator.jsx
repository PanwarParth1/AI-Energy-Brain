import { useEffect } from "react";
import { Play, RotateCcw } from "lucide-react";
import Header from "../components/layout/Header";
import { useLayout } from "../context/LayoutContext";
import Card from "../components/ui/Card";
import LoadingState from "../components/ui/LoadingState";
import ErrorState from "../components/ui/ErrorState";
import Badge from "../components/ui/Badge";
import { useSimulator } from "../hooks/useSimulator";
import BaselineCycleSelector from "../components/simulator/BaselineCycleSelector";
import SensorChangeRow from "../components/simulator/SensorChangeRow";
import ScenarioResultComparison from "../components/simulator/ScenarioResultComparison";
import ScenarioChangesSummary from "../components/simulator/ScenarioChangesSummary";
import SensorComparisonBarChart from "../components/simulator/SensorComparisonBarChart";
import ScenarioRecommendations from "../components/simulator/ScenarioRecommendations";
import { ApiError } from "../services/api";

export default function MachineSimulator() {
  const { setSidebarOpen } = useLayout();
  const sim = useSimulator();

  useEffect(() => {
    sim.init();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const availableToAdd = sim.sensorInfo?.sensors.filter(
    (s) => !sim.activeChanges.some((c) => c.sensor === s)
  ) ?? [];

  return (
    <div className="flex-1 overflow-y-auto">
      <Header
        onMenuClick={() => setSidebarOpen(true)}
        title="Machine What-If Simulator"
        subtitle="Modify real sensor readings and run them through the existing trained models - no retraining, no hardcoded outcomes."
      />

      <div className="space-y-6 p-8">
        {sim.initLoading && <LoadingState label="Loading simulator..." />}
        {sim.initError && (
          <ErrorState
            message={sim.initError instanceof ApiError ? sim.initError.message : "Unable to load the simulator."}
            onRetry={sim.init}
          />
        )}

        {sim.machine && !sim.initLoading && (
          <>
            <Card title={sim.machine.name} subtitle={`${sim.machine.source} - real cycles only, no fabricated machines`}>
              <BaselineCycleSelector
                maxCycleIndex={sim.machine.n_cycles_available - 1}
                currentCycleIndex={sim.baselineCycleIndex}
                loading={sim.baselineLoading}
                onLoad={(idx) => sim.loadBaselineCycle(idx, sim.machine.machine_id, sim.sensorInfo.sensors)}
              />

              {sim.baselineError && (
                <div className="mt-4">
                  <ErrorState
                    message={sim.baselineError instanceof ApiError ? sim.baselineError.message : "Unable to load baseline cycle."}
                  />
                </div>
              )}

              {sim.baselineStatus && !sim.baselineLoading && (
                <div className="mt-4 flex items-center gap-3 border-t border-slate-800 pt-4 text-sm">
                  <span className="text-slate-500">Current baseline status:</span>
                  <span className="text-slate-200">
                    {sim.baselineStatus.health.predicted_condition} - {sim.baselineStatus.health.predicted_condition_meaning}
                  </span>
                  <Badge label={sim.baselineStatus.anomaly.status} />
                </div>
              )}
            </Card>

            <Card
              title="Sensor Changes"
              subtitle="Only physical sensors can be modified - virtual/derived channels (CE, CP, SE) are excluded by the backend"
            >
              {sim.baselineLoading ? (
                <LoadingState label="Loading real baseline sensor values..." />
              ) : (
                <>
                  <div className="mb-4 flex items-center gap-2">
                    <select
                      onChange={(e) => {
                        if (e.target.value) sim.addChange(e.target.value);
                        e.target.value = "";
                      }}
                      disabled={sim.analyzeLoading || availableToAdd.length === 0}
                      defaultValue=""
                      className="border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-300 disabled:opacity-50"
                    >
                      <option value="" disabled>
                        {availableToAdd.length === 0 ? "All sensors added" : "+ Add sensor change..."}
                      </option>
                      {availableToAdd.map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </div>

                  {sim.activeChanges.length === 0 ? (
                    <p className="py-6 text-center text-sm text-slate-500">
                      No sensor changes yet. Add one above to start building a what-if scenario.
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {sim.activeChanges.map((change) => (
                        <SensorChangeRow
                          key={change.sensor}
                          change={change}
                          baseline={sim.baselineValues?.[change.sensor]}
                          disabled={sim.analyzeLoading}
                          onUpdate={(patch) => sim.updateChange(change.sensor, patch)}
                          onRemove={() => sim.removeChange(change.sensor)}
                        />
                      ))}
                    </div>
                  )}

                  <div className="mt-5 flex items-center gap-3 border-t border-slate-800 pt-4">
                    <button
                      onClick={sim.analyzeScenario}
                      disabled={sim.activeChanges.length === 0 || sim.analyzeLoading}
                      className="flex items-center gap-2 border border-cyan-700 bg-cyan-500/10 px-5 py-2.5 text-sm font-semibold text-cyan-300 transition hover:bg-cyan-500/20 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      <Play size={14} />
                      {sim.analyzeLoading ? "Analyzing sensor scenario..." : "ANALYZE SCENARIO"}
                    </button>
                    <button
                      onClick={sim.resetScenario}
                      disabled={sim.analyzeLoading || (sim.activeChanges.length === 0 && !sim.result)}
                      className="flex items-center gap-2 border border-slate-700 px-4 py-2.5 text-sm text-slate-400 transition hover:border-slate-500 hover:text-slate-200 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      <RotateCcw size={14} />
                      RESET SCENARIO
                    </button>
                  </div>

                  {sim.analyzeError && (
                    <div className="mt-4">
                      <ErrorState
                        message={sim.analyzeError instanceof ApiError ? sim.analyzeError.message : "Unable to analyze scenario."}
                        onRetry={sim.analyzeScenario}
                      />
                    </div>
                  )}
                </>
              )}
            </Card>

            {sim.analyzeLoading && (
              <Card><LoadingState label="Analyzing sensor scenario..." /></Card>
            )}

            {sim.result && !sim.analyzeLoading && (
              <>
                <Card title="Result: Baseline vs Simulated">
                  <ScenarioResultComparison result={sim.result} />
                </Card>

                <Card title="Scenario Changes" subtitle="Real before/after values from the model's own feature extraction">
                  <ScenarioChangesSummary changes={sim.result.changes} />
                </Card>

                <Card title="Sensor Comparison" subtitle="Baseline vs simulated cycle-mean, per changed sensor">
                  <SensorComparisonBarChart changes={sim.result.changes} />
                </Card>

                <Card
                  title="AI Recommendations"
                  subtitle="Scenario-specific - generated by the existing rule-based engine from the simulated results"
                >
                  <ScenarioRecommendations result={sim.result} />
                </Card>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
