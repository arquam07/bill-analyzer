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
      <div className="flex overflow-x-auto rounded border border-slate-200 bg-white overflow-hidden max-w-full">
        {PRESETS.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => setPreset(p)}
            className={
              "px-3 py-1.5 text-sm border-l first:border-l-0 border-slate-200 " +
              (preset === p
                ? "bg-slate-900 text-white"
                : "text-slate-700 hover:bg-slate-50")
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
            className="border border-slate-200 rounded px-2 py-1"
            aria-label="From date"
          />
          <span className="text-slate-500">to</span>
          <input
            type="date"
            value={customTo}
            onChange={(e) => setTo(e.target.value)}
            className="border border-slate-200 rounded px-2 py-1"
            aria-label="To date"
          />
        </div>
      )}
    </div>
  );
}
