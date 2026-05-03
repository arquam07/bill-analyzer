import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { InsightsBreakdownResponse } from "~/api/types";
import { useCurrency } from "./CurrencyContext";
import { formatMoney } from "./format";

interface Props {
  title: string;
  data: InsightsBreakdownResponse | undefined;
  isLoading: boolean;
  isError: boolean;
}

export function BreakdownChart({ title, data, isLoading, isError }: Props) {
  const { currency } = useCurrency();
  return (
    <div className="bg-white border border-slate-200 rounded p-4">
      <h2 className="text-sm font-semibold text-slate-900 mb-3">{title}</h2>
      <div className="h-64">
        {isLoading || !data ? (
          <div className="h-full grid place-items-center text-sm text-slate-400">
            Loading…
          </div>
        ) : isError ? (
          <div className="h-full grid place-items-center text-sm text-red-600">
            Could not load.
          </div>
        ) : data.rows.length === 0 ? (
          <div className="h-full grid place-items-center text-sm text-slate-400">
            No data in this period.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={data.rows}
              layout="vertical"
              margin={{ top: 4, right: 8, left: 8, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
              <XAxis
                type="number"
                tickFormatter={(v) => formatMoney(Number(v), currency)}
                stroke="#94a3b8"
                fontSize={12}
              />
              <YAxis
                type="category"
                dataKey="label"
                stroke="#94a3b8"
                fontSize={11}
                width={90}
              />
              <Tooltip
                formatter={(value) => formatMoney(Number(value), currency)}
                cursor={{ fill: "#f1f5f9" }}
              />
              <Bar dataKey="total" fill="#0f172a" radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
