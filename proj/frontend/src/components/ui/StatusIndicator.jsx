export default function StatusIndicator({ status, label }) {
  const map = {
    online: { dot: "bg-emerald-500", text: "text-emerald-400", label: label ?? "SYSTEM ONLINE" },
    offline: { dot: "bg-red-500", text: "text-red-400", label: label ?? "API OFFLINE" },
    checking: { dot: "bg-slate-500 animate-pulse", text: "text-slate-400", label: label ?? "CHECKING..." },
  };
  const s = map[status] ?? map.checking;
  return (
    <div className="flex items-center gap-2" role="status" aria-live="polite">
      <span className={`h-2 w-2 rounded-full ${s.dot}`} />
      <span className={`text-xs font-semibold tracking-wide ${s.text}`}>{s.label}</span>
    </div>
  );
}
