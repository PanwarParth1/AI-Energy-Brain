import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from "recharts";

/** changes: the real `changes` object from the API response -
 * {sensor: {baseline_mean, simulated_mean, unit, ...}}. Grouped bar
 * comparison, not a fabricated time series (Part 12 only returns
 * scalar cycle-level summaries, not raw waveforms, over the API). */
export default function SensorComparisonBarChart({ changes }) {
  if (!changes || Object.keys(changes).length === 0) return null;

  const data = Object.entries(changes).map(([sensor, c]) => ({
    sensor,
    Baseline: c.baseline_mean,
    Simulated: c.simulated_mean,
    unit: c.unit,
  }));

  return (
    <ResponsiveContainer width="100%" height={Math.max(180, data.length * 60)}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 24, left: 8, bottom: 4 }}>
        <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" stroke="#64748b" fontSize={11} tickLine={false} />
        <YAxis type="category" dataKey="sensor" stroke="#94a3b8" fontSize={11} width={56} tickLine={false} />
        <Tooltip
          contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", fontSize: 12 }}
          formatter={(value, name, props) => [`${value.toFixed(2)} ${props.payload.unit}`, name]}
        />
        <Legend wrapperStyle={{ fontSize: 11, color: "#94a3b8" }} />
        <Bar dataKey="Baseline" fill="#22d3ee" isAnimationActive={false} radius={[0, 2, 2, 0]} />
        <Bar dataKey="Simulated" fill="#fbbf24" isAnimationActive={false} radius={[0, 2, 2, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
