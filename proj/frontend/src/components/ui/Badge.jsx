import { statusColor } from "../../utils/format";

/** Text-and-color badge - never color alone (accessibility). */
export default function Badge({ label, tone }) {
  const c = statusColor(tone ?? label);
  return (
    <span
      className={`inline-flex items-center gap-1.5 border px-2 py-0.5 text-xs font-medium ${c.text} ${c.bg} ${c.border}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${c.dot}`} />
      {label}
    </span>
  );
}
