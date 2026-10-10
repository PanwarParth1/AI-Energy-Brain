import Badge from "../ui/Badge";

/** rec: one item from the actual recommendations API response shape:
 * {category, priority, title, action, reason, evidence, confidence,
 *  confidence_basis, machine_id, cycle_index, limitations, ...} */
export default function RecommendationCard({ rec, contextLabel }) {
  return (
    <div className="border border-slate-800 bg-slate-900/40 p-4">
      <div className="flex items-center justify-between">
        <Badge label={rec.priority} />
        <span className="text-[11px] uppercase tracking-wide text-slate-500">{rec.category.replaceAll("_", " ")}</span>
      </div>

      <h4 className="mt-2 text-sm font-semibold text-slate-100">{rec.title}</h4>
      <p className="mt-1 text-sm text-slate-300">{rec.action}</p>
      <p className="mt-1 text-xs text-slate-500">{rec.reason}</p>

      {rec.evidence?.length > 0 && (
        <ul className="mt-3 space-y-1 border-t border-slate-800 pt-2">
          {rec.evidence.map((e, i) => (
            <li key={i} className="text-xs text-slate-500">
              <span className="text-slate-400">{e.signal}:</span> {e.observation}
            </li>
          ))}
        </ul>
      )}

      <div className="mt-3 flex items-center justify-between text-[11px] text-slate-600">
        <span>
          {contextLabel ?? (rec.cycle_index != null ? `Cycle ${rec.cycle_index}` : rec.energy_datetime ? rec.energy_datetime : "—")}
        </span>
        <span title={rec.confidence_basis}>rule confidence {(rec.confidence * 100).toFixed(0)}%</span>
      </div>

      {rec.limitations?.length > 0 && (
        <p className="mt-2 text-[11px] italic text-slate-600">{rec.limitations[0]}</p>
      )}
    </div>
  );
}
