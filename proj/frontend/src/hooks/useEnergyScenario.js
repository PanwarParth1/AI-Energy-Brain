import { useCallback, useState } from "react";
import { api } from "../services/api";

const DEFAULT_BASELINE = { production: 1000, energy: 10000 };
const DEFAULT_SCENARIO = { production: 1500, energy: 15000 };

/** State for the Energy + Production What-If section (Part 14).
 *
 * Baseline/scenario inputs are manual numbers (the Tetouan dataset has
 * no production data - see README section 21) - never pulled from any
 * dataset or model. The only backend call is POST /energy/simulate,
 * made on "Analyze Scenario"; everything shown before that is a
 * client-side arithmetic PREVIEW (energy/production, one division),
 * matching the same preview-vs-authoritative-result pattern Part 13's
 * machine simulator already uses - the actual classification (NORMAL
 * vs WARNING) only ever comes from the real backend response.
 */
export function useEnergyScenario() {
  const [baseline, setBaseline] = useState(DEFAULT_BASELINE);
  const [scenario, setScenario] = useState(DEFAULT_SCENARIO);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const updateBaseline = useCallback((patch) => {
    setBaseline((prev) => ({ ...prev, ...patch }));
  }, []);

  const updateScenario = useCallback((patch) => {
    setScenario((prev) => ({ ...prev, ...patch }));
  }, []);

  const analyze = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.simulateEnergyProduction(
        baseline.production, baseline.energy, scenario.production, scenario.energy
      );
      setResult(data);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [baseline, scenario]);

  const reset = useCallback(() => {
    setBaseline(DEFAULT_BASELINE);
    setScenario(DEFAULT_SCENARIO);
    setResult(null);
    setError(null);
  }, []);

  return { baseline, scenario, result, loading, error, updateBaseline, updateScenario, analyze, reset };
}
