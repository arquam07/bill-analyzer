import type { Granularity } from "~/api/types";

export const PRESETS = ["7d", "30d", "3m", "6m", "12m", "custom"] as const;
export type Preset = (typeof PRESETS)[number];

export const PRESET_LABEL: Record<Preset, string> = {
  "7d": "7 days",
  "30d": "30 days",
  "3m": "3 months",
  "6m": "6 months",
  "12m": "12 months",
  custom: "Custom",
};

export const DEFAULT_PRESET: Preset = "30d";
export const MAX_RANGE_DAYS = 366;

export interface ResolvedRange {
  from: string; // YYYY-MM-DD
  to: string; // YYYY-MM-DD
}

function toIso(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function subDays(d: Date, n: number): Date {
  const out = new Date(d);
  out.setDate(out.getDate() - n);
  return out;
}

function subMonths(d: Date, n: number): Date {
  const out = new Date(d);
  out.setMonth(out.getMonth() - n);
  return out;
}

export function resolveRange(
  preset: Preset,
  customFrom: string | undefined,
  customTo: string | undefined,
): ResolvedRange {
  const today = new Date();
  if (preset === "custom" && customFrom && customTo) {
    return { from: customFrom, to: customTo };
  }
  switch (preset) {
    case "7d":
      return { from: toIso(subDays(today, 7)), to: toIso(today) };
    case "30d":
      return { from: toIso(subDays(today, 30)), to: toIso(today) };
    case "3m":
      return { from: toIso(subMonths(today, 3)), to: toIso(today) };
    case "6m":
      return { from: toIso(subMonths(today, 6)), to: toIso(today) };
    case "12m":
      return { from: toIso(subMonths(today, 12)), to: toIso(today) };
    case "custom":
      // fallback if custom dates missing — behave like 30d
      return { from: toIso(subDays(today, 30)), to: toIso(today) };
  }
}

export function durationDays(range: ResolvedRange): number {
  const from = new Date(range.from);
  const to = new Date(range.to);
  return Math.max(0, Math.round((to.getTime() - from.getTime()) / 86400000));
}

export function pickGranularity(range: ResolvedRange): Granularity {
  const days = durationDays(range);
  if (days <= 31) return "day";
  if (days <= 100) return "week";
  return "month";
}
