import Badge from "../ui/Badge";
import SensorDeviationChart from "../charts/SensorDeviationChart";
import { formatNumber } from "../../utils/format";

/** anomaly: the actual /machines/{id}/anomaly response shape. */
export default function AnomalyCard({ anomaly }) {
  if (!anomaly) return null;

  return (
    <div>
      <div className="flex items-center justify-between">
        <Badge label={anomaly.status} tone={anomaly.status} />
        <span className="text-xs text-slate-500">
          score {formatNumber(anomaly.anomaly_score, 3)}
        </span>
      </div>

      <p className="mt-3 text-xs text-slate-500">
        Reference condition: <span className="text-slate-300">{anomaly.reference_condition_meaning}</span>
      </p>
      <p className="mt-2 text-xs leading-relaxed text-slate-500">{anomaly.note}</p>

      {anomaly.top_deviations?.length > 0 && (
        <div className="mt-4">
          <SensorDeviationChart deviations={anomaly.top_deviations} />
        </div>
      )}
    </div>
  );
}
