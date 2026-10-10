import { useCallback, useState } from "react";
import { api, ApiError } from "../services/api";

const DEFAULT_MODE = "multiply";
const DEFAULT_MULTIPLY_VALUE = 1.5;

/**
 * All state for the What-If Simulator page in one hook.
 *
 * DESIGN NOTE on baseline sensor values: Part 12's API does not expose
 * a "give me the raw baseline reading for sensor X" endpoint - only
 * POST /machines/simulate, which returns per-sensor baseline_mean/
 * simulated_mean/unit inside `changes`, but only for sensors actually
 * perturbed in that request. To show REAL (never invented) baseline
 * values for every sensor before the user has changed anything, this
 * hook calls /machines/simulate once with an "identity" perturbation
 * (multiply x1.0) for every available sensor. That is a real backend
 * call using the exact existing request format - not a new endpoint,
 * not fabricated data - and its `changes[].baseline_mean` /
 * `.unit` values are what populates the sensor panel. This is discarded
 * after reading; the user's actual scenario is a separate, later call
 * built only from their chosen changes.
 */
export function useSimulator() {
  const [machine, setMachine] = useState(null);
  const [sensorInfo, setSensorInfo] = useState(null); // {sensors, valid_modes, excluded_virtual_sensors, note}
  const [baselineCycleIndex, setBaselineCycleIndex] = useState(null);
  const [baselineValues, setBaselineValues] = useState(null); // {sensor: {mean, unit}}
  const [baselineStatus, setBaselineStatus] = useState(null); // {health, anomaly} for the selected cycle
  const [activeChanges, setActiveChanges] = useState([]); // [{sensor, mode, value}]
  const [result, setResult] = useState(null); // last real /simulate response

  const [initLoading, setInitLoading] = useState(true);
  const [initError, setInitError] = useState(null);
  const [baselineLoading, setBaselineLoading] = useState(false);
  const [baselineError, setBaselineError] = useState(null);
  const [analyzeLoading, setAnalyzeLoading] = useState(false);
  const [analyzeError, setAnalyzeError] = useState(null);

  const loadBaselineCycle = useCallback(async (cycleIndex, machineId, sensors) => {
    setBaselineLoading(true);
    setBaselineError(null);
    setResult(null);
    try {
      const identityPerturbations = sensors.map((s) => ({
        sensor: s, mode: "multiply", value: 1.0,
      }));
      const data = await api.simulateMachine(machineId, cycleIndex, identityPerturbations);

      const values = {};
      for (const [sensor, change] of Object.entries(data.changes)) {
        values[sensor] = { mean: change.baseline_mean, unit: change.unit };
      }
      setBaselineValues(values);
      setBaselineStatus(data.baseline);
      setBaselineCycleIndex(cycleIndex);
      setActiveChanges([]);
    } catch (err) {
      setBaselineError(err);
    } finally {
      setBaselineLoading(false);
    }
  }, []);

  const init = useCallback(async () => {
    setInitLoading(true);
    setInitError(null);
    try {
      const [machinesData, sensorsData] = await Promise.all([
        api.getMachines(),
        api.getSimulatableSensors(),
      ]);
      const m = machinesData.machines[0];
      setMachine(m);
      setSensorInfo(sensorsData);

      // Real, backend-confirmed default cycle: whichever cycle the
      // existing health endpoint already defaults to when no
      // cycle_index is given (see Machine Health page - same pattern).
      const defaultHealth = await api.getMachineHealth(m.machine_id);
      await loadBaselineCycle(defaultHealth.cycle_index, m.machine_id, sensorsData.sensors);
    } catch (err) {
      setInitError(err);
    } finally {
      setInitLoading(false);
    }
  }, [loadBaselineCycle]);

  const addChange = useCallback((sensor) => {
    setActiveChanges((prev) =>
      prev.some((c) => c.sensor === sensor)
        ? prev
        : [...prev, { sensor, mode: DEFAULT_MODE, value: DEFAULT_MULTIPLY_VALUE }]
    );
  }, []);

  const updateChange = useCallback((sensor, patch) => {
    setActiveChanges((prev) => prev.map((c) => (c.sensor === sensor ? { ...c, ...patch } : c)));
  }, []);

  const removeChange = useCallback((sensor) => {
    setActiveChanges((prev) => prev.filter((c) => c.sensor !== sensor));
  }, []);

  const analyzeScenario = useCallback(async () => {
    if (!machine || baselineCycleIndex == null || activeChanges.length === 0) return;
    setAnalyzeLoading(true);
    setAnalyzeError(null);
    // Clear the previous scenario first so its results/recommendations can never be
    // shown as current - including if this analysis fails.
    setResult(null);
    try {
      const perturbations = activeChanges.map(({ sensor, mode, value }) => ({ sensor, mode, value }));
      const data = await api.simulateMachine(machine.machine_id, baselineCycleIndex, perturbations);
      setResult(data);
    } catch (err) {
      setAnalyzeError(err);
    } finally {
      setAnalyzeLoading(false);
    }
  }, [machine, baselineCycleIndex, activeChanges]);

  const resetScenario = useCallback(() => {
    setActiveChanges([]);
    setResult(null);
    setAnalyzeError(null);
  }, []);

  return {
    machine, sensorInfo, baselineCycleIndex, baselineValues, baselineStatus,
    activeChanges, result,
    initLoading, initError, baselineLoading, baselineError, analyzeLoading, analyzeError,
    init, loadBaselineCycle, addChange, updateChange, removeChange, analyzeScenario, resetScenario,
  };
}
