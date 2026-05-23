import { Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { bills as billsApi } from "~/api/endpoints";
import type { BillStatus } from "~/api/types";

const STATUS_BADGE: Record<BillStatus, string> = {
  uploaded: "bg-slate-200 text-slate-700",
  extracted: "bg-amber-100 text-amber-800",
  reviewed: "bg-emerald-100 text-emerald-800",
};

function StatusBadge({ status }: { status: string }) {
  const cls = STATUS_BADGE[status as BillStatus] ?? "bg-slate-200 text-slate-700";
  return (
    <span className={`text-xs uppercase tracking-wide rounded px-2 py-0.5 ${cls}`}>
      {status}
    </span>
  );
}

export function BillsList() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["bills"],
    queryFn: () => billsApi.list({ limit: 50 }),
  });

  if (isLoading) return <p className="text-slate-500">Loading bills…</p>;
  if (error) return <p className="text-red-600">Error loading bills.</p>;
  if (!data) return null;

  if (data.items.length === 0) {
    return (
      <div className="border border-dashed border-slate-300 rounded p-8 text-center">
        <p className="text-slate-600">No bills yet.</p>
        <Link to="/upload" className="inline-block mt-3 text-slate-900 underline">
          Upload your first bill
        </Link>
      </div>
    );
  }

  return (
    <ul className="divide-y divide-slate-200 bg-card border border-slate-200 rounded-2xl overflow-hidden shadow-card">
      {data.items.map((b) => (
        <li key={b.id}>
          <Link
            to="/bills/$billId"
            params={{ billId: b.id }}
            className="flex items-center justify-between px-4 py-4 hover:bg-slate-50"
          >
            <div className="min-w-0">
              <div className="font-medium truncate">
                {b.merchant ?? <span className="text-slate-400">(unnamed)</span>}
              </div>
              <div className="text-xs text-slate-500">
                {b.billed_at
                  ? new Date(b.billed_at + "T12:00:00").toLocaleDateString(undefined, {
                      year: "numeric",
                      month: "short",
                      day: "numeric",
                    })
                  : "—"}
              </div>
            </div>
            <div className="flex items-center gap-3">
              {b.total !== null && b.total !== undefined && (
                <span className="font-mono text-sm">
                  {b.currency ?? ""} {b.total.toFixed(2)}
                </span>
              )}
              <StatusBadge status={b.status} />
            </div>
          </Link>
        </li>
      ))}
    </ul>
  );
}
