import { useState } from "react";
import { ApiError } from "~/api/fetcher";
import type {
  FriendRequestResponse,
  SettlementResponse,
  SplitRequestResponse,
} from "~/api/types";
import { useAuth } from "~/auth/AuthContext";
import {
  useAcceptFriendRequest,
  useAcceptRequest,
  useAcceptSettlement,
  useBalances,
  useIncomingFriendRequests,
  useIncomingRequests,
  useIncomingSettlements,
  useOutgoingRequests,
  useOutgoingSettlements,
  useRejectFriendRequest,
  useRejectRequest,
  useRejectSettlement,
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
    <div className="border border-slate-200 rounded-2xl p-4 space-y-2 bg-card">
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
            className="flex-1 bg-emerald-700 text-white text-sm rounded-lg px-3 py-2.5 disabled:opacity-50 font-medium"
          >
            {accept.isPending ? "…" : "Accept"}
          </button>
          <button
            type="button"
            disabled={reject.isPending}
            onClick={() => reject.mutate(req.id)}
            className="flex-1 bg-card border border-slate-300 text-sm rounded-lg px-3 py-2.5 disabled:opacity-50 hover:bg-red-50 hover:border-red-300 hover:text-red-700"
          >
            {reject.isPending ? "…" : "Decline"}
          </button>
        </div>
      )}
    </div>
  );
}

function SettlementCard({
  settlement,
  currentUsername,
}: {
  settlement: SettlementResponse;
  currentUsername: string;
}) {
  const accept = useAcceptSettlement();
  const reject = useRejectSettlement();
  const isIncoming = settlement.initiated_by_username !== currentUsername;
  const isPending = settlement.status === "pending";

  // Determine the human-readable claim, from the viewer's perspective.
  let title: string;
  if (isIncoming) {
    // counterparty initiated. They are initiated_by.
    if (settlement.from_username === settlement.initiated_by_username) {
      // they claim they paid us
      title = `@${settlement.initiated_by_username} says they paid you ${settlement.amount.toFixed(2)}`;
    } else {
      // they claim they received from us
      title = `@${settlement.initiated_by_username} says they received ${settlement.amount.toFixed(2)} from you`;
    }
  } else {
    // we initiated.
    if (settlement.from_username === currentUsername) {
      // we claimed we paid them
      title = `You paid @${settlement.to_username} ${settlement.amount.toFixed(2)}`;
    } else {
      // we claimed we received from them
      title = `You received ${settlement.amount.toFixed(2)} from @${settlement.from_username}`;
    }
  }

  return (
    <div className="border border-slate-200 rounded-2xl p-4 space-y-2 bg-card">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-medium">{title}</p>
          <p className="text-xs text-slate-400 mt-0.5">
            {new Date(settlement.created_at).toLocaleDateString()}
            {" · "}
            <span className="uppercase tracking-wide">Settlement</span>
          </p>
          {settlement.note && (
            <p className="text-xs text-slate-500 italic mt-1 truncate">
              {settlement.note}
            </p>
          )}
        </div>
        <div className="text-right shrink-0">
          <span
            className={`inline-block text-xs uppercase tracking-wide rounded px-2 py-0.5 ${STATUS_BADGE[settlement.status] ?? ""}`}
          >
            {settlement.status}
          </span>
        </div>
      </div>

      {isIncoming && isPending && (
        <div className="flex gap-2 pt-1">
          <button
            type="button"
            disabled={accept.isPending}
            onClick={() => accept.mutate(settlement.id)}
            className="flex-1 bg-emerald-700 text-white text-sm rounded-lg px-3 py-2.5 disabled:opacity-50 font-medium"
          >
            {accept.isPending ? "…" : "Confirm"}
          </button>
          <button
            type="button"
            disabled={reject.isPending}
            onClick={() => reject.mutate(settlement.id)}
            className="flex-1 bg-card border border-slate-300 text-sm rounded-lg px-3 py-2.5 disabled:opacity-50 hover:bg-red-50 hover:border-red-300 hover:text-red-700"
          >
            {reject.isPending ? "…" : "Dispute"}
          </button>
        </div>
      )}
    </div>
  );
}

function SettleForm({ username }: { username: string }) {
  const settle = useSettle();
  const [direction, setDirection] = useState<"paid" | "received">("paid");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
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

  function reset() {
    setOpen(false);
    setAmount("");
    setNote("");
    setDirection("paid");
  }

  return (
    <form
      className="space-y-2 pt-2"
      onSubmit={(e) => {
        e.preventDefault();
        const n = parseFloat(amount);
        if (!n || n <= 0) return;
        settle.mutate(
          {
            username,
            amount: n,
            direction,
            note: note.trim() || undefined,
          },
          { onSuccess: reset },
        );
      }}
    >
      <div className="inline-flex rounded-lg bg-slate-100 p-0.5 text-xs">
        <button
          type="button"
          onClick={() => setDirection("paid")}
          className={`px-3 py-1.5 rounded-md font-medium transition-colors ${direction === "paid"
              ? "bg-card text-slate-900 shadow-sm"
              : "text-slate-500 hover:text-slate-700"
            }`}
        >
          I paid @{username}
        </button>
        <button
          type="button"
          onClick={() => setDirection("received")}
          className={`px-3 py-1.5 rounded-md font-medium transition-colors ${direction === "received"
              ? "bg-card text-slate-900 shadow-sm"
              : "text-slate-500 hover:text-slate-700"
            }`}
        >
          I received from @{username}
        </button>
      </div>
      <div className="flex gap-2 items-center flex-wrap">
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
        <input
          type="text"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Note (optional)"
          maxLength={256}
          className="flex-1 min-w-[160px] border border-slate-300 rounded px-2 py-1 text-sm"
        />
      </div>
      {settle.error && (
        <p className="text-xs text-red-600">
          {settle.error instanceof ApiError ? settle.error.detail : "Failed to send."}
        </p>
      )}
      <div className="flex gap-2 items-center">
        <button
          type="submit"
          disabled={settle.isPending || !amount}
          className="bg-slate-900 text-white text-xs rounded-lg px-3 py-1.5 font-medium disabled:opacity-50 hover:bg-slate-800 transition-colors"
        >
          {settle.isPending ? "Sending…" : "Send request"}
        </button>
        <button
          type="button"
          onClick={reset}
          className="text-slate-400 hover:text-slate-700 text-sm"
        >
          Cancel
        </button>
      </div>
      <p className="text-[11px] text-slate-400">
        Goes to @{username} for confirmation. Balance updates only after they confirm.
      </p>
    </form>
  );
}

function FriendRequestCard({ fr }: { fr: FriendRequestResponse }) {
  const accept = useAcceptFriendRequest();
  const reject = useRejectFriendRequest();

  return (
    <div className="border border-slate-200 rounded-2xl p-4 space-y-2 bg-card">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium">
            <span className="text-slate-500">From</span> <span>@{fr.requester_username}</span>
          </p>
          <p className="text-xs text-slate-400 mt-0.5">
            {new Date(fr.created_at).toLocaleDateString()}
          </p>
        </div>
        <span className="text-xs bg-blue-50 text-blue-700 rounded px-2 py-0.5 uppercase tracking-wide">
          Friend request
        </span>
      </div>
      <div className="flex gap-2">
        <button
          type="button"
          disabled={accept.isPending}
          onClick={() => accept.mutate(fr.id)}
          className="flex-1 bg-emerald-700 text-white text-sm rounded-lg px-3 py-2.5 disabled:opacity-50 font-medium"
        >
          {accept.isPending ? "…" : "Accept"}
        </button>
        <button
          type="button"
          disabled={reject.isPending}
          onClick={() => reject.mutate(fr.id)}
          className="flex-1 bg-card border border-slate-300 text-sm rounded-lg px-3 py-2.5 disabled:opacity-50 hover:bg-red-50 hover:border-red-300 hover:text-red-700"
        >
          {reject.isPending ? "…" : "Decline"}
        </button>
      </div>
    </div>
  );
}

export function SplitsTab({ enabled = true }: { enabled?: boolean }) {
  const { user } = useAuth();
  const currentUsername = user?.username ?? "";

  const incoming = useIncomingRequests(enabled);
  const outgoing = useOutgoingRequests(enabled);
  const balances = useBalances(enabled);
  const friendRequests = useIncomingFriendRequests(enabled);
  const incomingSettlements = useIncomingSettlements(enabled);
  const outgoingSettlements = useOutgoingSettlements(enabled);

  const pendingIn = incoming.data?.items.filter((r) => r.status === "pending") ?? [];
  const declinedIn = incoming.data?.items.filter((r) => r.status === "rejected") ?? [];
  const outgoingItems = outgoing.data?.items ?? [];
  const pendingFriendRequests = friendRequests.data?.items ?? [];

  const incomingSettleItems = incomingSettlements.data?.items ?? [];
  const outgoingSettleItems = outgoingSettlements.data?.items ?? [];
  const pendingOutgoingSettlements = outgoingSettleItems.filter(
    (s) => s.status === "pending",
  );
  const declinedOutgoingSettlements = outgoingSettleItems.filter(
    (s) => s.status === "rejected",
  );

  const isLoading =
    incoming.isLoading ||
    outgoing.isLoading ||
    balances.isLoading ||
    friendRequests.isLoading ||
    incomingSettlements.isLoading ||
    outgoingSettlements.isLoading;
  if (isLoading) return <p className="text-slate-500">Loading…</p>;

  const loadError =
    incoming.error ??
    outgoing.error ??
    balances.error ??
    incomingSettlements.error ??
    outgoingSettlements.error;
  if (loadError) {
    return (
      <p className="text-red-600">
        {loadError instanceof ApiError ? loadError.detail : "Error loading splits."}
      </p>
    );
  }

  const everythingEmpty =
    pendingIn.length === 0 &&
    outgoingItems.length === 0 &&
    pendingFriendRequests.length === 0 &&
    (balances.data?.balances.length ?? 0) === 0 &&
    incomingSettleItems.length === 0 &&
    outgoingSettleItems.length === 0;

  return (
    <div className="space-y-8">
      {/* Incoming friend requests */}
      {pendingFriendRequests.length > 0 && (
        <section className="space-y-3">
          <h2 className="font-medium text-slate-800">
            Friend requests{" "}
            <span className="ml-1 bg-blue-100 text-blue-800 text-xs rounded-full px-2 py-0.5">
              {pendingFriendRequests.length}
            </span>
          </h2>
          <div className="space-y-2">
            {pendingFriendRequests.map((fr) => (
              <FriendRequestCard key={fr.id} fr={fr} />
            ))}
          </div>
        </section>
      )}

      {/* Balances */}
      {(balances.data?.balances.length ?? 0) > 0 && (
        <section className="space-y-3">
          <h2 className="font-medium text-slate-800">Balances</h2>
          <ul className="divide-y divide-slate-100 border border-slate-200 rounded bg-card">
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

      {/* Incoming settlement requests (need confirmation) */}
      {incomingSettleItems.length > 0 && (
        <section className="space-y-3">
          <h2 className="font-medium text-slate-800">
            Payment confirmations{" "}
            <span className="ml-1 bg-amber-100 text-amber-800 text-xs rounded-full px-2 py-0.5">
              {incomingSettleItems.length}
            </span>
          </h2>
          <div className="space-y-2">
            {incomingSettleItems.map((s) => (
              <SettlementCard
                key={s.id}
                settlement={s}
                currentUsername={currentUsername}
              />
            ))}
          </div>
        </section>
      )}

      {/* Incoming pending split requests */}
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

      {/* Outgoing (split + settlement) */}
      {(outgoingItems.length > 0 || pendingOutgoingSettlements.length > 0) && (
        <section className="space-y-3">
          <h2 className="font-medium text-slate-800">Sent requests</h2>
          <div className="space-y-2">
            {pendingOutgoingSettlements.map((s) => (
              <SettlementCard
                key={s.id}
                settlement={s}
                currentUsername={currentUsername}
              />
            ))}
            {outgoingItems.map((r) => (
              <RequestCard key={r.id} req={r} direction="outgoing" />
            ))}
          </div>
        </section>
      )}

      {/* Declined (split + settlement) */}
      {(declinedIn.length > 0 || declinedOutgoingSettlements.length > 0) && (
        <section className="space-y-3">
          <h2 className="font-medium text-slate-400">Declined</h2>
          <div className="space-y-2">
            {declinedIn.map((r) => (
              <RequestCard key={r.id} req={r} direction="incoming" />
            ))}
            {declinedOutgoingSettlements.map((s) => (
              <SettlementCard
                key={s.id}
                settlement={s}
                currentUsername={currentUsername}
              />
            ))}
          </div>
        </section>
      )}

      {everythingEmpty && (
        <p className="text-sm text-slate-500">
          No split activity yet. Split a bill from the bill detail page.
        </p>
      )}
    </div>
  );
}
