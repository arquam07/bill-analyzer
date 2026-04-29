import type { InsightsOverviewResponse } from "~/api/types";
import { formatDelta, formatMoney } from "./format";

interface Props {
  data: InsightsOverviewResponse | undefined;
  isLoading: boolean;
  isError: boolean;
}

function Card({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: React.ReactNode;
}) {
  return (
    <div className="bg-white border border-slate-200 rounded p-4">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-900">{value}</div>
      {sub && <div className="mt-1 text-xs text-slate-500">{sub}</div>}
    </div>
  );
}

function Skeleton() {
  return (
    <div className="bg-white border border-slate-200 rounded p-4">
      <div className="h-3 w-16 bg-slate-200 rounded animate-pulse" />
      <div className="mt-2 h-7 w-24 bg-slate-200 rounded animate-pulse" />
      <div className="mt-2 h-3 w-20 bg-slate-200 rounded animate-pulse" />
    </div>
  );
}

export function KpiCards({ data, isLoading, isError }: Props) {
  if (isLoading || !data) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} />
        ))}
      </div>
    );
  }
  if (isError) {
    return (
      <div className="bg-white border border-red-200 rounded p-4 text-sm text-red-700">
        Could not load summary.
      </div>
    );
  }

  const delta = formatDelta(data.spend_delta_pct);
  const deltaTone =
    delta.tone === "up"
      ? "text-emerald-600"
      : delta.tone === "down"
        ? "text-rose-600"
        : "text-slate-500";

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
      <Card
        label="Total spend"
        value={formatMoney(data.total_spend)}
        sub={
          <span>
            <span className={deltaTone}>{delta.text}</span> vs prior period
          </span>
        }
      />
      <Card label="Bills" value={String(data.bill_count)} />
      <Card label="Avg bill" value={formatMoney(data.avg_bill)} />
      <Card
        label="Top merchant"
        value={data.top_merchant ?? "—"}
        sub={data.top_category ? <span>Top category: {data.top_category}</span> : undefined}
      />
    </div>
  );
}
