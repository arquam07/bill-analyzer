import type { InsightsTopItemsResponse, ItemOrderBy } from "~/api/types";
import { useCurrency } from "./CurrencyContext";
import { formatMoney } from "./format";

interface Props {
  data: InsightsTopItemsResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  orderBy: ItemOrderBy;
  onOrderByChange: (next: ItemOrderBy) => void;
  onSelect?: (row: { normalized_name: string; name: string }) => void;
}

function titleCase(s: string): string {
  return s.replace(/\b\w/g, (c) => c.toUpperCase());
}

export function TopItemsTable({
  data,
  isLoading,
  isError,
  orderBy,
  onOrderByChange,
  onSelect,
}: Props) {
  const { currency } = useCurrency();
  return (
    <div className="bg-card border border-slate-200 rounded-2xl shadow-card">
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
        <h2 className="font-serif font-semibold text-[16px] tracking-[-0.01em] text-slate-900">Top items</h2>
        <div className="inline-flex bg-slate-50 rounded-lg p-0.5 text-xs gap-0.5">
          {(["spend", "frequency"] as const).map((o) => (
            <button
              key={o}
              type="button"
              onClick={() => onOrderByChange(o)}
              className={
                "px-2.5 py-1 rounded-md font-medium transition-all " +
                (orderBy === o
                  ? "bg-card shadow-sm text-slate-900"
                  : "text-slate-500 hover:text-slate-800")
              }
            >
              by {o}
            </button>
          ))}
        </div>
      </div>
      <div className="px-6 py-4">
        {isLoading || !data ? (
          <div className="text-sm text-slate-400">Loading…</div>
        ) : isError ? (
          <div className="text-sm text-red-600">Could not load.</div>
        ) : data.rows.length === 0 ? (
          <div className="text-sm text-slate-400">No items in this period.</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-500">
                <th className="font-medium pb-2">Item</th>
                <th className="font-medium pb-2 text-right">Spend</th>
                <th className="font-medium pb-2 text-right">Bought</th>
                <th className="font-medium pb-2 text-right">Last</th>
              </tr>
            </thead>
            <tbody>
              {data.rows.map((row) => (
                <tr
                  key={row.normalized_name}
                  className={
                    "border-t border-slate-100" +
                    (onSelect ? " cursor-pointer hover:bg-slate-50" : "")
                  }
                  onClick={
                    onSelect
                      ? () => onSelect({ normalized_name: row.normalized_name, name: row.name })
                      : undefined
                  }
                >
                  <td className="py-2 truncate max-w-[180px]">
                    {titleCase(row.normalized_name) || row.name}
                  </td>
                  <td className="py-2 text-right font-mono">
                    {formatMoney(row.total_spend, currency)}
                  </td>
                  <td className="py-2 text-right text-slate-600">
                    {row.purchase_count}
                  </td>
                  <td className="py-2 text-right text-slate-500 text-xs">
                    {row.last_purchased
                      ? new Date(row.last_purchased).toLocaleDateString()
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
