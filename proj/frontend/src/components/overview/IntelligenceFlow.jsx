import { ArrowRight, Database, Brain, Search, GitBranch, Bell, UserCheck } from "lucide-react";

const STEPS = [
  { icon: Database, label: "Data", sub: "Tetouan + Hydraulic" },
  { icon: Brain, label: "Energy + Machine Intelligence", sub: "Forecast - Health" },
  { icon: Search, label: "Anomaly / Efficiency Analysis", sub: "IsolationForest - Intensity" },
  { icon: GitBranch, label: "Decision Engine", sub: "Rule-based" },
  { icon: Bell, label: "Alerts + Recommendations", sub: "" },
  { icon: UserCheck, label: "Operator Action", sub: "" },
];

/** Purely presentational - a compact technical diagram of the
 * platform's real data flow, not a marketing graphic. No API calls.
 *
 * Mobile-first responsive note: each step is a (box, arrow) pair.
 * Below `sm`, the pair stacks vertically (flex-col) with the arrow
 * rotated 90deg to point down; at `sm` and above, the pair is a row
 * (box then arrow side by side) and the outer container switches from
 * a vertical stack to a wrapping horizontal row.
 */
export default function IntelligenceFlow() {
  return (
    <div className="flex flex-col items-stretch gap-2 sm:flex-row sm:flex-wrap lg:overflow-x-auto">
      {STEPS.map((step, i) => (
        <div key={step.label} className="flex flex-col items-center gap-2 sm:flex-row">
          <div className="flex min-w-[120px] flex-1 flex-col items-center gap-1.5 border border-slate-800 bg-slate-950/60 px-3 py-3 text-center">
            <step.icon size={16} className="text-cyan-500" />
            <span className="text-[11px] font-medium leading-tight text-slate-300">{step.label}</span>
            {step.sub && <span className="text-[10px] text-slate-600">{step.sub}</span>}
          </div>
          {i < STEPS.length - 1 && (
            <ArrowRight size={14} className="shrink-0 rotate-90 text-slate-700 sm:rotate-0" />
          )}
        </div>
      ))}
    </div>
  );
}
