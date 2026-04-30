import { useState } from "react";
import { ApiError } from "~/api/fetcher";
import type { SplitRequestResponse } from "~/api/types";
import {
  useAcceptRequest,
  useBalances,
  useIncomingRequests,
  useOutgoingRequests,
  useRejectRequest,
  useSettle,
} from "./api";

const STATUS_BADGE: Record<string, string> = {
  pending: "bg-amber-100 text-amber-800",
  accepted: "bg-emerald-100 text-emerald-800",
  rejected: "bg-red-100 text-red-700",
};

function RequestCard({
  req,
  direction,
}: {
  req: SplitRequestResponse;
  direction: "incoming" | "outgoing";
}) {
  const accept = useAcceptRequest();
  const reject = useRejectRequest();
  const isPending = req.status === "pending";

  return (
    <div className="border border-slate-200 rounded p-4 space-y-2 bg-white">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-medium truncate">
            {direction === "incoming" ? (
              <>
                <span className="text-slate-500">From</span>{" "}
                <span>@{req.from_username}</span>
              </>
            ) : (
              <>
                <span className="text-slate-500">To</span>{" "}
                <span>@{req.to_username}</span>
              </>
            )}
          </p>
          <p className="text-xs text-slate-500 truncate">
            {req.bill.merchant ?? "(unnamed bill)"}
            {req.bill.billed_at && ` · ${req.bill.billed_at}`}
          </p>
          {req.note && req.note !== req.bill.merchant && (
            <p className="text-xs text-slate-400 italic truncate">{req.note}</p>
          )}
        </div>
        <div className="text-right shrink-0 space-y-1">
          <p className="font-mono font-semibold">{req.amount.toFixed(2)}</p>
          <span
            className={`inline-block text-xs uppercase tracking-wide rounded px-2 py-0.5 ${STATUS_BADGE[req.status] ?? ""}`}
          >
            {req.status}
          </span>
        </div>
      </div>

      {direction === "incoming" && isPending && (
        <div className="flex gap-2 pt-1">
          <button
            type="button"
            disabled={accept.isPending}
            onClick={() => accept.mutate(req.id)}
            className="flex-1 bg-emerald-700 text-white text-sm rounded px-3 py-1.5 disabled:opacity-50"
          >
            {accept.isPending ? "…" : "Accept"}
          </button>
          <button
            type="button"
            disabled={reject.isPending}
            onClick={() => reject.mutate(req.id)}
            className="flex-1 bg-white border border-slate-300 text-sm rounded px-3 py-1.5 disabled:opacity-50 hover:bg-red-50 hover:border-red-300 hover:text-red-700"
          >
            {reject.isPending ? "…" : "Decline"}
          </button>
        </div>
      )}
    </div>
  );
}

function SettleForm({ username }: { username: string }) {
  const settle = useSettle();
  const [amount, setAmount] = useState("");
  const [open, setOpen] = useState(false);

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="text-xs text-slate-500 hover:text-slate-800 underline"
      >
        Record payment
      </button>
    );
  }

  return (
    <form
      className="flex gap-2 items-center"
      onSubmit={(e) => {
        e.preventDefault();
        const n = parseFloat(amount);
        if (!n || n <= 0) return;
        settle.mutate(
          { username, amount: n },
          { onSuccess: () => { setOpen(false); setAmount(""); } },
        );
      }}
    >
      <input
        type="number"
        step="0.01"
        min="0.01"
        value={amount}
        onChange={(e) => setAmount(e.target.value)}
        placeholder="Amount"
        className="w-28 border border-slate-300 rounded px-2 py-1 text-sm"
        autoFocus
      />
      <button
        type="submit"
        disabled={settle.isPending || !amount}
        className="bg-slate-800 text-white text-xs rounded px-3 py-1.5 disabled:opacity-50"
      >
        {settle.isPending ? "…" : "Mark paid"}
      </button>
      <button
        type="button"
        onClick={() => setOpen(false)}
        className="text-slate-400 hover:text-slate-700 text-sm"
      >
        Cancel
      </button>
    </form>
  );
}

export function SplitsTab({ enabled = true }: { enabled?: boolean }) {
  const incoming = useIncomingRequests(enabled);
  const outgoing = useOutgoingRequests(enabled);
  const balances = useBalances(enabled);

  const pendingIn = incoming.data?.items.filter((r) => r.status === "pending") ?? [];
  const declinedIn = incoming.data?.items.filter((r) => r.status === "rejected") ?? [];
  const outgoingItems = outgoing.data?.items ?? [];

  const isLoading = incoming.isLoading || outgoing.isLoading || balances.isLoading;
  if (isLoading) return <p className="text-slate-500">Loading…</p>;

  const loadError = incoming.error ?? outgoing.error ?? balances.error;
  if (loadError) {
    return (
      <p className="text-red-600">
        {loadError instanceof ApiError ? loadError.detail : "Error loading splits."}
      </p>
    );
  }

  return (
    <div className="space-y-8">
      {/* Balances */}
      {(balances.data?.balances.length ?? 0) > 0 && (
        <section className="space-y-3">
          <h2 className="font-medium text-slate-800">Balances</h2>
          <ul className="divide-y divide-slate-100 border border-slate-200 rounded bg-white">
            {balances.data!.balances.map((b) => (
              <li key={b.user_id} className="px-4 py-3 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">@{b.username}</span>
                  <span
                    className={`font-mono font-semibold text-sm ${b.net > 0 ? "text-emerald-700" : "text-red-600"}`}
                  >
                    {b.net > 0 ? `+${b.net.toFixed(2)}` : b.net.toFixed(2)}
                  </span>
                </div>
                <div className="text-xs text-slate-500">
                  {b.net > 0
                    ? `@${b.username} owes you ${b.net.toFixed(2)}`
                    : `You owe @${b.username} ${Math.abs(b.net).toFixed(2)}`}
                </div>
                <SettleForm username={b.username} />
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Incoming pending */}
      <section className="space-y-3">
        <h2 className="font-medium text-slate-800">
          Pending requests{" "}
          {pendingIn.length > 0 && (
            <span className="ml-1 bg-amber-100 text-amber-800 text-xs rounded-full px-2 py-0.5">
              {pendingIn.length}
            </span>
          )}
        </h2>
        {pendingIn.length === 0 ? (
          <p className="text-sm text-slate-500">No pending requests.</p>
        ) : (
          <div className="space-y-2">
            {pendingIn.map((r) => (
              <RequestCard key={r.id} req={r} direction="incoming" />
            ))}
          </div>
        )}
      </section>

      {/* Outgoing */}
      {outgoingItems.length > 0 && (
        <section className="space-y-3">
          <h2 className="font-medium text-slate-800">Sent requests</h2>
          <div className="space-y-2">
            {outgoingItems.map((r) => (
              <RequestCard key={r.id} req={r} direction="outgoing" />
            ))}
          </div>
        </section>
      )}

      {/* Declined */}
      {declinedIn.length > 0 && (
        <section className="space-y-3">
          <h2 className="font-medium text-slate-800 text-slate-400">Declined</h2>
          <div className="space-y-2">
            {declinedIn.map((r) => (
              <RequestCard key={r.id} req={r} direction="incoming" />
            ))}
          </div>
        </section>
      )}

      {pendingIn.length === 0 &&
        outgoingItems.length === 0 &&
        (balances.data?.balances.length ?? 0) === 0 && (
          <p className="text-sm text-slate-500">
            No split activity yet. Split a bill from the bill detail page.
          </p>
        )}
    </div>
  );
}
