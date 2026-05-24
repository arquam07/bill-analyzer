const fmtCache = new Map<string, Intl.NumberFormat>();

function getMoneyFmt(currency: string): Intl.NumberFormat {
  let fmt = fmtCache.get(currency);
  if (!fmt) {
    fmt = new Intl.NumberFormat(undefined, {
      style: "currency",
      currency,
      currencyDisplay: "narrowSymbol",
    });
    fmtCache.set(currency, fmt);
  }
  return fmt;
}

export function formatMoney(value: number, currency = "JPY"): string {
  return getMoneyFmt(currency).format(value);
}

export function formatDelta(pct: number | null): { text: string; tone: "up" | "down" | "flat" } {
  if (pct === null || !Number.isFinite(pct)) return { text: "—", tone: "flat" };
  const tone = pct > 0 ? "up" : pct < 0 ? "down" : "flat";
  const sign = pct > 0 ? "+" : "";
  return { text: `${sign}${pct.toFixed(1)}%`, tone };
}

export function formatPeriodLabel(iso: string, granularity: "day" | "week" | "month"): string {
  const d = new Date(iso);
  if (granularity === "month") {
    return d.toLocaleDateString(undefined, { month: "short", year: "numeric" });
  }
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
