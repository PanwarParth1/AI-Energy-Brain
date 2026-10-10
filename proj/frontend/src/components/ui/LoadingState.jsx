export default function LoadingState({ label = "Loading..." }) {
  return (
    <div className="flex items-center gap-3 py-10 text-sm text-slate-400" role="status" aria-live="polite">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-700 border-t-cyan-400" />
      {label}
    </div>
  );
}
