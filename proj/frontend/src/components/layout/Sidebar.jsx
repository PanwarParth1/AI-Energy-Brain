import { NavLink } from "react-router-dom";
import { LayoutDashboard, Zap, Cpu, Bell, ClipboardList, FlaskConical, X } from "lucide-react";
import StatusIndicator from "../ui/StatusIndicator";
import { useApiHealth } from "../../hooks/useApiHealth";

// Grouped conceptually (Part 15) - same routes/behaviour as before,
// just organized under small section labels for scan-ability. No
// route was added, removed, or renamed.
const NAV_GROUPS = [
  {
    label: "Monitor",
    items: [
      { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
      { to: "/energy", label: "Energy Intelligence", icon: Zap },
      { to: "/machines", label: "Machine Health", icon: Cpu },
    ],
  },
  {
    label: "Simulate",
    items: [
      { to: "/machine-simulator", label: "Machine Simulator", icon: FlaskConical },
    ],
  },
  {
    label: "Decide",
    items: [
      { to: "/alerts", label: "Alerts", icon: Bell },
      { to: "/recommendations", label: "Recommendations", icon: ClipboardList },
    ],
  },
];

export default function Sidebar({ open, onClose }) {
  const { status } = useApiHealth();

  return (
    <>
      {/* Mobile scrim - closes the drawer on tap outside */}
      {open && (
        <div
          className="fixed inset-0 z-30 bg-black/60 lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex h-screen w-60 shrink-0 flex-col border-r border-slate-800 bg-slate-950 transition-transform duration-200 lg:static lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-5">
          <div>
            <p className="text-sm font-bold tracking-widest text-slate-100">AI ENERGY BRAIN</p>
            <p className="mt-0.5 text-[11px] text-slate-500">Industrial Intelligence</p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close navigation"
            className="text-slate-500 hover:text-slate-300 lg:hidden"
          >
            <X size={18} />
          </button>
        </div>

        <nav className="flex-1 space-y-4 px-3 py-4">
          {NAV_GROUPS.map((group) => (
            <div key={group.label}>
              <p className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-wider text-slate-600">
                {group.label}
              </p>
              <div className="space-y-1">
                {group.items.map(({ to, label, icon: Icon, end }) => (
                  <NavLink
                    key={to}
                    to={to}
                    end={end}
                    onClick={onClose}
                    className={({ isActive }) =>
                      `flex items-center gap-3 px-3 py-2.5 text-sm transition ${
                        isActive
                          ? "border-l-2 border-cyan-400 bg-slate-900 text-cyan-300"
                          : "border-l-2 border-transparent text-slate-400 hover:bg-slate-900/60 hover:text-slate-200"
                      }`
                    }
                  >
                    <Icon size={16} strokeWidth={2} />
                    {label}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>

        <div className="border-t border-slate-800 px-5 py-4">
          <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-600">
            System Status
          </p>
          <StatusIndicator status={status} label={status === "online" ? "API Connected" : status === "offline" ? "API Offline" : "Checking..."} />
        </div>
      </aside>
    </>
  );
}
