import { PRESETS, PRESET_LABEL, type Preset } from "./range";

interface Props {
  preset: Preset;
  customFrom: string;
  customTo: string;
  onChange: (next: { preset: Preset; customFrom: string; customTo: string }) => void;
}

export function TimeRangePicker({ preset, customFrom, customTo, onChange }: Props) {
  const setPreset = (p: Preset) => onChange({ preset: p, customFrom, customTo });
  const setFrom = (v: string) => onChange({ preset: "custom", customFrom: v, customTo });
  const setTo = (v: string) => onChange({ preset: "custom", customFrom, customTo: v });

  return (
    <div className="flex flex-col sm:flex-row sm:flex-wrap sm:items-center gap-2">
      <div className="inline-flex bg-card border border-slate-200 rounded-[10px] p-1 gap-0.5 overflow-x-auto max-w-full">
        {PRESETS.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => setPreset(p)}
            className={
              "px-3.5 py-1.5 text-[13.5px] font-medium rounded-[7px] transition-all duration-150 whitespace-nowrap " +
              (preset === p
                ? "bg-slate-900 text-slate-50 shadow-sm"
                : "text-slate-600 hover:text-slate-900 hover:bg-slate-100")
            }
          >
            {PRESET_LABEL[p]}
          </button>
        ))}
      </div>
      {preset === "custom" && (
        <div className="flex items-center gap-2 text-sm">
          <input
            type="date"
            value={customFrom}
            onChange={(e) => setFrom(e.target.value)}
            className="border border-slate-200 rounded-lg px-2.5 py-1.5 text-sm bg-card"
            aria-label="From date"
          />
          <span className="text-slate-400">to</span>
          <input
            type="date"
            value={customTo}
            onChange={(e) => setTo(e.target.value)}
            className="border border-slate-200 rounded-lg px-2.5 py-1.5 text-sm bg-card"
            aria-label="To date"
          />
        </div>
      )}
    </div>
  );
}
