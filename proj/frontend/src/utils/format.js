export function formatNumber(value, decimals = 0) {
  if (value == null || Number.isNaN(value)) return "Data unavailable";
  return value.toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function formatTimestamp(value) {
  if (!value) return "Data unavailable";
  const d = new Date(value.replace(" ", "T"));
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatTime(value) {
  if (!value) return "";
  const d = new Date(value.replace(" ", "T"));
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

/** Priority/status -> semantic color token, used consistently across
 * badges, borders and chart bars. Never invented per-component. */
export const STATUS_COLORS = {
  CRITICAL: { text: "text-red-400", bg: "bg-red-500/15", border: "border-red-500/40", dot: "bg-red-500" },
  HIGH: { text: "text-red-400", bg: "bg-red-500/15", border: "border-red-500/40", dot: "bg-red-500" },
  ANOMALY: { text: "text-red-400", bg: "bg-red-500/15", border: "border-red-500/40", dot: "bg-red-500" },
  WARNING: { text: "text-amber-400", bg: "bg-amber-500/15", border: "border-amber-500/40", dot: "bg-amber-500" },
  MEDIUM: { text: "text-amber-400", bg: "bg-amber-500/15", border: "border-amber-500/40", dot: "bg-amber-500" },
  LOW: { text: "text-blue-400", bg: "bg-blue-500/15", border: "border-blue-500/40", dot: "bg-blue-500" },
  NORMAL: { text: "text-emerald-400", bg: "bg-emerald-500/15", border: "border-emerald-500/40", dot: "bg-emerald-500" },
  INFO: { text: "text-slate-400", bg: "bg-slate-500/15", border: "border-slate-500/40", dot: "bg-slate-500" },
};

export function statusColor(status) {
  return STATUS_COLORS[status] ?? STATUS_COLORS.INFO;
}
