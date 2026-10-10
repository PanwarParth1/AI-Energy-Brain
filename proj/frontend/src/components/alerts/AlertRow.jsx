import Badge from "../ui/Badge";

/** One alert row - extracted from the Alerts page (Part 15) so Overview
 * can show the same real alert data without a second implementation. */
export default function AlertRow({ alert }) {
  return (
    <div className="flex items-start justify-between border border-slate-800 bg-slate-950/40 p-4">
      <div>
        <Badge label={alert.severity} />
        <p className="mt-2 text-sm font-medium text-slate-200">{alert.title}</p>
        <p className="mt-1 text-xs text-slate-500">
          {alert.category.replaceAll("_", " ")} - {alert.machine_id}
          {alert.cycle_index != null && ` - cycle ${alert.cycle_index}`}
        </p>
      </div>
      <span className="text-[11px] text-slate-600">{alert.source}</span>
    </div>
  );
}
