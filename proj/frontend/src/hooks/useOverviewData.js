import { useFetch } from "./useFetch";
import { api } from "../services/api";

/** Combines the calls the Overview page needs into one loading/error
 * state. Each call hits a real, already-tested backend endpoint. */
export function useOverviewData() {
  return useFetch(async () => {
    const [dashboard, alerts, history] = await Promise.all([
      api.getDashboardSummary(),
      api.getAlerts(),
      api.getEnergyHistory({ limit: 144 }), // trailing 24h at 10-min steps
    ]);
    return { dashboard, alerts, history };
  }, []);
}
