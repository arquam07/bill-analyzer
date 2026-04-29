import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Granularity, InsightsTimeseriesResponse } from "~/api/types";
import { formatMoney, formatPeriodLabel } from "./format";

interface Props {
  data: InsightsTimeseriesResponse | undefined;
  granularity: Granularity;
  isLoading: boolean;
  isError: boolean;
}

export function SpendOverTimeChart({ data, granularity, isLoading, isError }: Props) {
  return (
    <div className="bg-white border border-slate-200 rounded p-4">
      <div className="flex items-baseline justify-between mb-3">
        <h2 className="text-sm font-semibold text-slate-900">Spend over time</h2>
        <span className="text-xs text-slate-500">by {granularity}</span>
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
            <LineChart
              data={data.points}
              margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
              <XAxis
                dataKey="period"
                tickFormatter={(v) => formatPeriodLabel(v, granularity)}
                stroke="#94a3b8"
                fontSize={12}
              />
              <YAxis
                tickFormatter={(v) => formatMoney(Number(v))}
                stroke="#94a3b8"
                fontSize={12}
                width={70}
              />
              <Tooltip
                formatter={(value) => formatMoney(Number(value))}
                labelFormatter={(label) => formatPeriodLabel(String(label), granularity)}
              />
              <Line
                type="monotone"
                dataKey="total"
                stroke="#0f172a"
                strokeWidth={2}
                dot={{ r: 3 }}
                activeDot={{ r: 5 }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
