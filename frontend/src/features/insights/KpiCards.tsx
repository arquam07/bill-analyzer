import type { InsightsOverviewResponse } from "~/api/types";
import { useCurrency } from "./CurrencyContext";
import { formatDelta, formatMoney } from "./format";

interface CardProps {
  label: string;
  value: string;
  valueSerif?: boolean;
  sub?: React.ReactNode;
}

function Card({ label, value, valueSerif, sub }: CardProps) {
  return (
    <div className="bg-card border border-slate-200 rounded-2xl p-[18px] shadow-card hover:shadow-card-hover hover:-translate-y-0.5 transition-all duration-200">
      <div className="font-mono text-[11px] tracking-[0.06em] uppercase text-slate-400 mb-3">
        {label}
      </div>
      <div
        className={`font-mono text-[28px] font-semibold leading-none tracking-tight text-slate-900 ${
          valueSerif ? "font-serif text-[21px] leading-snug tracking-[-0.01em]" : ""
        }`}
      >
        {value}
      </div>
      {sub && <div className="mt-2.5 text-[12.5px] text-slate-400 flex items-center gap-1.5">{sub}</div>}
    </div>
  );
}

function DeltaChip({ tone, text }: { tone: "up" | "down" | "flat"; text: string }) {
  if (tone === "flat") {
    return (
      <span className="inline-flex items-center font-mono text-[11.5px] font-semibold px-2 py-0.5 rounded-md bg-slate-100 text-slate-400">
        {text}
      </span>
    );
  }
  if (tone === "up") {
    return (
      <span className="inline-flex items-center font-mono text-[11.5px] font-semibold px-2 py-0.5 rounded-md bg-[#e6f1ea] text-[#1f7a55]">
        ↑ {text}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center font-mono text-[11.5px] font-semibold px-2 py-0.5 rounded-md bg-accent-soft text-accent-deep">
      ↓ {text}
    </span>
  );
}

function Skeleton() {
  return (
    <div className="bg-card border border-slate-200 rounded-2xl p-[18px] shadow-card">
      <div className="h-2.5 w-14 bg-slate-200 rounded animate-pulse mb-3" />
      <div className="h-7 w-24 bg-slate-200 rounded animate-pulse" />
      <div className="mt-3 h-2.5 w-20 bg-slate-200 rounded animate-pulse" />
    </div>
  );
}

export function KpiCards({ data, isLoading, isError }: {
  data: InsightsOverviewResponse | undefined;
  isLoading: boolean;
  isError: boolean;
}) {
  if (isLoading || !data) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
        {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} />)}
      </div>
    );
  }
  if (isError) {
    return (
      <div className="bg-card border border-red-200 rounded-xl p-4 text-sm text-red-700">
        Could not load summary.
      </div>
    );
  }

  const { currency } = useCurrency();
  const delta = formatDelta(data.spend_delta_pct);

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
        <Card
          label="Total spend"
          value={formatMoney(data.total_spend, currency)}
          sub={
            <span className="flex items-center gap-1.5">
              <DeltaChip tone={delta.tone} text={delta.text} />
              <span>vs prior period</span>
            </span>
          }
        />
        <Card label="Bills" value={String(data.bill_count)} sub={<span>across {data.bill_count} bills</span>} />
        <Card label="Avg bill" value={formatMoney(data.avg_bill, currency)} />
        <Card
          label="Top merchant"
          value={data.top_merchant ?? "—"}
          valueSerif={Boolean(data.top_merchant)}
          sub={
            data.top_category ? (
              <span>
                Top category:{" "}
                <span className="text-accent-deep font-semibold">{data.top_category}</span>
              </span>
            ) : undefined
          }
        />
      </div>
      {data.bills_missing_date > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-800">
          {data.bills_missing_date} reviewed{" "}
          {data.bills_missing_date === 1 ? "bill is" : "bills are"} missing a date and excluded
          from insights. Open the bill and set the date to include it.
        </div>
      )}
    </div>
  );
}
