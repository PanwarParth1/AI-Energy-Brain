import { X } from "lucide-react";
import { formatNumber } from "../../utils/format";

/** One active perturbation row: sensor name, real baseline value, a
 * mode/value control, and a CLIENT-COMPUTED preview (clearly labelled
 * as a preview - the authoritative number only comes back after
 * Analyze Scenario actually calls the real model). */
export default function SensorChangeRow({ change, baseline, onUpdate, onRemove, disabled }) {
  const baselineMean = baseline?.mean;
  const unit = baseline?.unit ?? "";

  const preview =
    baselineMean == null
      ? null
      : change.mode === "multiply"
      ? baselineMean * change.value
      : baselineMean + change.value;

  return (
    <div className="flex flex-col gap-3 border border-slate-800 bg-slate-950/40 px-3 py-2.5 lg:grid lg:grid-cols-12 lg:items-center">
      <div className="flex items-center justify-between lg:col-span-2 lg:block">
        <div>
          <p className="text-sm font-medium text-slate-200">{change.sensor}</p>
          <p className="text-[11px] text-slate-600">
            Baseline: {baselineMean != null ? formatNumber(baselineMean, 2) : "..."} {unit}
          </p>
        </div>
        <button
          onClick={onRemove}
          disabled={disabled}
          aria-label={`Remove ${change.sensor} change`}
          className="text-slate-500 hover:text-red-400 disabled:opacity-50 lg:hidden"
        >
          <X size={16} />
        </button>
      </div>

      <select
        value={change.mode}
        onChange={(e) => onUpdate({ mode: e.target.value })}
        disabled={disabled}
        className="w-full border border-slate-700 bg-slate-950 px-2 py-1.5 text-xs text-slate-300 disabled:opacity-50 lg:col-span-3"
      >
        <option value="multiply">Multiply (×)</option>
        <option value="offset">Offset (+/-)</option>
      </select>

      <div className="flex items-center gap-2 lg:col-span-3">
        <input
          type="range"
          min={change.mode === "multiply" ? 0.1 : -50}
          max={change.mode === "multiply" ? 10 : 50}
          step={change.mode === "multiply" ? 0.1 : 0.5}
          value={change.value}
          onChange={(e) => onUpdate({ value: Number(e.target.value) })}
          disabled={disabled}
          className="w-full accent-cyan-500 disabled:opacity-50"
        />
        <input
          type="number"
          value={change.value}
          onChange={(e) => onUpdate({ value: Number(e.target.value) })}
          disabled={disabled}
          step={change.mode === "multiply" ? 0.1 : 0.5}
          className="w-16 shrink-0 border border-slate-700 bg-slate-950 px-1.5 py-1 text-xs text-slate-300 disabled:opacity-50"
        />
      </div>

      <div className="text-xs lg:col-span-3">
        <span className="text-slate-500">Preview: </span>
        <span className="font-medium text-amber-300">
          {preview != null ? formatNumber(preview, 2) : "..."} {unit}
        </span>
        <span className="ml-1 text-[10px] text-slate-600">(client preview, not yet analyzed)</span>
      </div>

      <button
        onClick={onRemove}
        disabled={disabled}
        aria-label={`Remove ${change.sensor} change`}
        className="hidden text-slate-500 hover:text-red-400 disabled:opacity-50 lg:col-span-1 lg:flex lg:justify-end"
      >
        <X size={16} />
      </button>
    </div>
  );
}
