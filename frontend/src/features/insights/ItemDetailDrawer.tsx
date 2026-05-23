import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Granularity } from "~/api/types";
import { useCurrency } from "./CurrencyContext";
import { useItemTimeseries } from "./api";
import { formatMoney, formatPeriodLabel } from "./format";

interface Props {
  normalizedName: string | null;
  displayName: string;
  from: string;
  to: string;
  granularity: Granularity;
  onClose: () => void;
}

export function ItemDetailDrawer({
  normalizedName,
  displayName,
  from,
  to,
  granularity,
  onClose,
}: Props) {
  const { currency } = useCurrency();
  const { data, isLoading, isError } = useItemTimeseries(
    normalizedName,
    from,
    to,
    granularity,
  );

  if (normalizedName === null) return null;

  return (
    <>
      {/* backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-40"
        onClick={onClose}
        aria-hidden
      />
      {/* panel */}
      <div className="fixed inset-y-0 right-0 w-full max-w-sm bg-card border-l border-slate-200 shadow-xl z-50 flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-slate-200">
          <h2 className="text-sm font-semibold text-slate-900 truncate">{displayName}</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 text-lg leading-none ml-2"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {isLoading || !data ? (
            <div className="text-sm text-slate-400">Loading…</div>
          ) : isError ? (
            <div className="text-sm text-red-600">Could not load item details.</div>
          ) : (
            <>
              {/* summary stats */}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-slate-50 rounded p-3">
                  <div className="text-xs text-slate-500 mb-1">Total spend</div>
                  <div className="text-lg font-semibold font-mono">
                    {formatMoney(data.total_spend, currency)}
                  </div>
                </div>
                <div className="bg-slate-50 rounded p-3">
                  <div className="text-xs text-slate-500 mb-1">Times bought</div>
                  <div className="text-lg font-semibold">{data.purchase_count}</div>
                </div>
                {data.purchase_count > 0 && (
                  <div className="bg-slate-50 rounded p-3">
                    <div className="text-xs text-slate-500 mb-1">Avg per purchase</div>
                    <div className="text-lg font-semibold font-mono">
                      {formatMoney(data.total_spend / data.purchase_count, currency)}
                    </div>
                  </div>
                )}
              </div>

              {/* timeseries chart */}
              {data.points.length === 0 ? (
                <div className="text-sm text-slate-400 text-center py-6">
                  No purchases in this period.
                </div>
              ) : (
                <div>
                  <h3 className="text-xs font-medium text-slate-500 mb-2 uppercase tracking-wide">
                    Spend over time
                  </h3>
                  <div className="h-48">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart
                        data={data.points}
                        margin={{ top: 4, right: 4, left: 0, bottom: 0 }}
                      >
                        <XAxis
                          dataKey="period"
                          tickFormatter={(v) => formatPeriodLabel(v, granularity)}
                          stroke="#8a8378"
                          fontSize={11}
                        />
                        <YAxis
                          tickFormatter={(v) => formatMoney(Number(v), currency)}
                          stroke="#8a8378"
                          fontSize={11}
                          width={60}
                        />
                        <Tooltip
                          formatter={(value) => formatMoney(Number(value), currency)}
                          labelFormatter={(label) => formatPeriodLabel(String(label), granularity)}
                          cursor={{ stroke: "#f1ede5" }}
                        />
                        <Line
                          type="monotone"
                          dataKey="total"
                          stroke="#e0533d"
                          strokeWidth={2}
                          dot={false}
                          activeDot={{ r: 4 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}
