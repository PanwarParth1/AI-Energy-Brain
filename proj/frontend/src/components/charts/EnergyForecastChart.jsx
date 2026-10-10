import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine,
} from "recharts";
import { formatTime, formatNumber } from "../../utils/format";

/** historyRecords: recent real records (for context).
 * forecastPoints: [{timestamp, value}] - the model's predictions.
 * Historical and forecast series are rendered distinctly (solid vs dashed). */
export default function EnergyForecastChart({ historyRecords, forecastPoints }) {
  if (!forecastPoints || forecastPoints.length === 0) return null;

  const historyData = (historyRecords ?? []).map((r) => ({
    label: formatTime(r.timestamp),
    historical: r.total_power_consumption,
  }));
  const forecastData = forecastPoints.map((p) => ({
    label: formatTime(p.timestamp),
    forecast: p.value,
  }));
  const data = [...historyData, ...forecastData];
  const splitLabel = historyData.length > 0 ? historyData[historyData.length - 1].label : null;

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="label" stroke="#64748b" fontSize={11} tickLine={false} />
        <YAxis
          stroke="#64748b"
          fontSize={11}
          tickLine={false}
          tickFormatter={(v) => formatNumber(v / 1000, 0) + "k"}
          width={48}
        />
        <Tooltip
          contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", fontSize: 12 }}
          labelStyle={{ color: "#94a3b8" }}
          formatter={(value, name) => [formatNumber(value, 1), name]}
        />
        <Legend wrapperStyle={{ fontSize: 11, color: "#94a3b8" }} />
        {splitLabel && <ReferenceLine x={splitLabel} stroke="#475569" strokeDasharray="4 4" />}
        <Line type="monotone" dataKey="historical" name="Historical" stroke="#22d3ee" strokeWidth={2} dot={false} isAnimationActive={false} connectNulls />
        <Line type="monotone" dataKey="forecast" name="Forecast" stroke="#fbbf24" strokeWidth={2} strokeDasharray="5 4" dot={{ r: 2 }} isAnimationActive={false} connectNulls />
      </LineChart>
    </ResponsiveContainer>
  );
}
