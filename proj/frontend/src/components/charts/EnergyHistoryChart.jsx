import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from "recharts";
import { formatTime, formatNumber } from "../../utils/format";

/** records: [{timestamp, total_power_consumption, zone_1_power_consumption, ...}]
 * showZones: whether to render the three zone lines alongside total. */
export default function EnergyHistoryChart({ records, showZones = false }) {
  if (!records || records.length === 0) return null;

  const data = records.map((r) => ({
    ...r,
    label: formatTime(r.timestamp),
  }));

  return (
    <ResponsiveContainer width="100%" height={320}>
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
        <Line
          type="monotone"
          dataKey="total_power_consumption"
          name="Total"
          stroke="#22d3ee"
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
        {showZones && (
          <Line type="monotone" dataKey="zone_1_power_consumption" name="Zone 1" stroke="#60a5fa" strokeWidth={1.25} dot={false} isAnimationActive={false} />
        )}
        {showZones && (
          <Line type="monotone" dataKey="zone_2_power_consumption" name="Zone 2" stroke="#a78bfa" strokeWidth={1.25} dot={false} isAnimationActive={false} />
        )}
        {showZones && (
          <Line type="monotone" dataKey="zone_3_power_consumption" name="Zone 3" stroke="#fbbf24" strokeWidth={1.25} dot={false} isAnimationActive={false} />
        )}
      </LineChart>
    </ResponsiveContainer>
  );
}
