import { Menu } from "lucide-react";
import { useApiHealth } from "../../hooks/useApiHealth";
import StatusIndicator from "../ui/StatusIndicator";

export default function Header({ title, subtitle, onMenuClick }) {
  const { status, lastChecked } = useApiHealth();

  return (
    <header className="flex items-center justify-between border-b border-slate-800 bg-slate-950/80 px-4 py-5 sm:px-8">
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          aria-label="Open navigation"
          className="text-slate-400 hover:text-slate-200 lg:hidden"
        >
          <Menu size={20} />
        </button>
        <div>
          <h1 className="text-base font-semibold text-slate-100 sm:text-lg">{title}</h1>
          {subtitle && <p className="mt-1 hidden text-sm text-slate-500 sm:block">{subtitle}</p>}
        </div>
      </div>
      <div className="text-right">
        <StatusIndicator status={status} />
        <p className="mt-1 hidden text-[11px] text-slate-600 sm:block">
          {lastChecked ? `Last checked: ${lastChecked.toLocaleTimeString()}` : "Checking..."}
        </p>
      </div>
    </header>
  );
}
