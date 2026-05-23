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
  barColor?: string;
}

export function BreakdownChart({ title, data, isLoading, isError, barColor = "#e0533d" }: Props) {
  const { currency } = useCurrency();
  return (
    <div className="bg-card border border-slate-200 rounded-2xl p-6 shadow-card">
      <h2 className="font-serif font-semibold text-[16px] tracking-[-0.01em] text-slate-900 mb-5">
        {title}
      </h2>
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
              <CartesianGrid strokeDasharray="3 3" stroke="#f1ede5" horizontal={false} />
              <XAxis
                type="number"
                tickFormatter={(v) => formatMoney(Number(v), currency)}
                stroke="#938b7f"
                fontSize={11}
                fontFamily="'Spline Sans Mono', monospace"
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="label"
                stroke="#938b7f"
                fontSize={11}
                width={90}
                tickLine={false}
              />
              <Tooltip
                formatter={(value) => formatMoney(Number(value), currency)}
                cursor={{ fill: "#f1ede5" }}
                contentStyle={{
                  background: "#1c1a17",
                  border: "none",
                  borderRadius: 8,
                  padding: "8px 12px",
                }}
                labelStyle={{ color: "#938b7f", fontFamily: "'Spline Sans Mono', monospace", fontSize: 11 }}
                itemStyle={{ color: "#faf9f6", fontFamily: "'Spline Sans Mono', monospace", fontSize: 13, fontWeight: 600 }}
              />
              <Bar dataKey="total" fill={barColor} radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
