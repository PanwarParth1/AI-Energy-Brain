import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell } from "recharts";

/** deviations: [{feature, z_score, ...}] from the anomaly endpoint's
 * top_deviations - real z-scores, never invented. Bars colored by
 * direction (above/below reference), not by an invented "severity". */
export default function SensorDeviationChart({ deviations }) {
  if (!deviations || deviations.length === 0) return null;

  const data = [...deviations]
    .sort((a, b) => Math.abs(b.z_score) - Math.abs(a.z_score))
    .map((d) => ({ name: d.feature, z: d.z_score }));

  return (
    <div>
      <ResponsiveContainer width="100%" height={Math.max(160, data.length * 34)}>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 24, left: 8, bottom: 4 }}>
          <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" stroke="#64748b" fontSize={11} tickLine={false} />
          <YAxis type="category" dataKey="name" stroke="#94a3b8" fontSize={11} width={120} tickLine={false} />
          <Tooltip
            contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", fontSize: 12 }}
            formatter={(value) => [`z = ${value.toFixed(2)}`, "Statistical deviation from reference"]}
          />
          <Bar dataKey="z" isAnimationActive={false} radius={[0, 2, 2, 0]}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.z >= 0 ? "#f87171" : "#60a5fa"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <p className="mt-2 text-[11px] text-slate-500">
        Top statistical deviations from the learned reference sensor behaviour (z-score). Not a root-cause diagnosis.
      </p>
    </div>
  );
}
