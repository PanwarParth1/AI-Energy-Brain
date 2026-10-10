import { Link } from "react-router-dom";
import { FlaskConical, Calculator, ArrowRight } from "lucide-react";

const CARDS = [
  {
    icon: FlaskConical,
    title: "Machine What-If",
    description: "Test how sensor changes affect machine health and anomaly detection.",
    cta: "Open Machine Simulator",
    to: "/machine-simulator",
  },
  {
    icon: Calculator,
    title: "Energy + Production What-If",
    description: "Test whether higher energy use is proportional to higher production.",
    cta: "Open Energy What-If",
    to: "/energy",
  },
];

/** Compact navigation cards - no simulator logic here, just discovery
 * and a link. The real forms live on their own pages (Parts 13/14). */
export default function WhatIfAccessCards() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      {CARDS.map((card) => (
        <Link
          key={card.to}
          to={card.to}
          className="group flex flex-col justify-between border border-slate-800 bg-slate-900/60 p-5 transition hover:border-cyan-700"
        >
          <div>
            <card.icon size={18} className="text-cyan-500" />
            <p className="mt-3 text-sm font-semibold text-slate-200">{card.title}</p>
            <p className="mt-1.5 text-xs leading-relaxed text-slate-500">{card.description}</p>
          </div>
          <div className="mt-4 flex items-center gap-1.5 text-xs font-medium text-cyan-400 group-hover:gap-2.5 transition-all">
            {card.cta}
            <ArrowRight size={13} />
          </div>
        </Link>
      ))}
    </div>
  );
}
