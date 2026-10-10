export default function ErrorState({ message, onRetry }) {
  return (
    <div className="flex flex-col items-start gap-3 border border-red-900/50 bg-red-950/20 px-4 py-4 text-sm">
      <p className="text-red-300">{message || "Something went wrong."}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="border border-red-800 px-3 py-1.5 text-xs font-medium text-red-300 transition hover:bg-red-900/30"
        >
          Retry
        </button>
      )}
    </div>
  );
}
