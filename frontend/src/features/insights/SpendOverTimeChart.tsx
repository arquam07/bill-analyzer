import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Granularity, InsightsTimeseriesResponse } from "~/api/types";
import { useCurrency } from "./CurrencyContext";
import { formatMoney, formatPeriodLabel } from "./format";

interface Props {
  data: InsightsTimeseriesResponse | undefined;
  granularity: Granularity;
  isLoading: boolean;
  isError: boolean;
}

export function SpendOverTimeChart({ data, granularity, isLoading, isError }: Props) {
  const { currency } = useCurrency();
  return (
    <div className="bg-card border border-slate-200 rounded-2xl p-6 shadow-card">
      <div className="flex items-baseline justify-between mb-5">
        <h2 className="font-serif font-semibold text-[18px] tracking-[-0.01em] text-slate-900">
          Spend over time
        </h2>
        <span className="font-mono text-xs text-slate-400">by {granularity}</span>
      </div>
      <div className="h-64">
        {isLoading || !data ? (
          <div className="h-full grid place-items-center text-sm text-slate-400">
            Loading chart…
          </div>
        ) : isError ? (
          <div className="h-full grid place-items-center text-sm text-red-600">
            Could not load chart.
          </div>
        ) : data.points.length === 0 ? (
          <div className="h-full grid place-items-center text-sm text-slate-400">
            No spend in this period.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={data.points}
              margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
            >
              <defs>
                <linearGradient id="spendGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#e0533d" stopOpacity={0.14} />
                  <stop offset="95%" stopColor="#e0533d" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1ede5" vertical={false} />
              <XAxis
                dataKey="period"
                tickFormatter={(v) => formatPeriodLabel(v, granularity)}
                stroke="#938b7f"
                fontSize={11}
                fontFamily="'Spline Sans Mono', monospace"
                tickLine={false}
              />
              <YAxis
                tickFormatter={(v) => formatMoney(Number(v), currency)}
                stroke="#938b7f"
                fontSize={11}
                fontFamily="'Spline Sans Mono', monospace"
                width={72}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                formatter={(value) => formatMoney(Number(value), currency)}
                labelFormatter={(label) => formatPeriodLabel(String(label), granularity)}
                contentStyle={{
                  background: "#1c1a17",
                  border: "none",
                  borderRadius: 8,
                  padding: "8px 12px",
                }}
                labelStyle={{ color: "#938b7f", fontFamily: "'Spline Sans Mono', monospace", fontSize: 11 }}
                itemStyle={{ color: "#faf9f6", fontFamily: "'Spline Sans Mono', monospace", fontSize: 13, fontWeight: 600 }}
              />
              <Area
                type="linear"
                dataKey="total"
                stroke="#e0533d"
                strokeWidth={2.5}
                fill="url(#spendGradient)"
                dot={{ r: 3, fill: "#fff", stroke: "#e0533d", strokeWidth: 2 }}
                activeDot={{ r: 5, fill: "#e0533d" }}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
