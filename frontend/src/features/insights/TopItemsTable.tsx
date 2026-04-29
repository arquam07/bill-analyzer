import type { InsightsTopItemsResponse, ItemOrderBy } from "~/api/types";
import { formatMoney } from "./format";

interface Props {
  data: InsightsTopItemsResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  orderBy: ItemOrderBy;
  onOrderByChange: (next: ItemOrderBy) => void;
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
}: Props) {
  return (
    <div className="bg-white border border-slate-200 rounded">
      <div className="flex items-center justify-between p-4 border-b border-slate-200">
        <h2 className="text-sm font-semibold text-slate-900">Top items</h2>
        <div className="inline-flex rounded border border-slate-200 overflow-hidden text-xs">
          {(["spend", "frequency"] as const).map((o) => (
            <button
              key={o}
              type="button"
              onClick={() => onOrderByChange(o)}
              className={
                "px-2 py-1 border-l first:border-l-0 border-slate-200 " +
                (orderBy === o
                  ? "bg-slate-900 text-white"
                  : "text-slate-700 hover:bg-slate-50")
              }
            >
              by {o}
            </button>
          ))}
        </div>
      </div>
      <div className="p-4">
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
                <tr key={row.normalized_name} className="border-t border-slate-100">
                  <td className="py-2 truncate max-w-[180px]">
                    {titleCase(row.normalized_name) || row.name}
                  </td>
                  <td className="py-2 text-right font-mono">
                    {formatMoney(row.total_spend)}
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
