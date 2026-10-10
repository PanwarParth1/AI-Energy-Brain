export default function Card({ title, subtitle, action, children, className = "" }) {
  return (
    <div className={`border border-slate-800 bg-slate-900/60 ${className}`}>
      {(title || action) && (
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-3">
          <div>
            {title && <h3 className="text-sm font-semibold tracking-wide text-slate-200">{title}</h3>}
            {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
          </div>
          {action}
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  );
}
