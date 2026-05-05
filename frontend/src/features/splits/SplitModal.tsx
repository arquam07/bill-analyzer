import { useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { friends as friendsApi, splitRequests as api } from "~/api/endpoints";
import { ApiError } from "~/api/fetcher";
import type { BillItemResponse, NonFriendInfo, RecipientAssignment } from "~/api/types";

interface Props {
  billId: string;
  total: number;
  merchant: string | null;
  items: BillItemResponse[];
  onClose: () => void;
  onSuccess: () => void;
}

interface AddedUser {
  id: string;
  username: string;
  name: string | null;
}

type SplitMode = "equal" | "assign";

export function SplitModal({ billId, total, merchant, items, onClose, onSuccess }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [rawInput, setRawInput] = useState("");
  const [users, setUsers] = useState<AddedUser[]>([]);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [isLooking, setIsLooking] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [nonFriendQueue, setNonFriendQueue] = useState<NonFriendInfo[] | null>(null);

  // Split mode
  const [mode, setMode] = useState<SplitMode>("equal");
  // assign mode: username → set of item IDs assigned to that person
  const [assignments, setAssignments] = useState<Record<string, Set<string>>>({});

  const friendsQuery = useQuery({
    queryKey: ["friends"],
    queryFn: () => friendsApi.list(),
  });
  const friendsList = friendsQuery.data?.friends ?? [];

  const suggestions = rawInput.length >= 1
    ? friendsList
        .filter((f) => f.username.startsWith(rawInput) && !users.some((u) => u.username === f.username))
        .slice(0, 6)
    : [];

  const itemsWithPrice = items.filter((it) => it.total_price !== null && it.total_price !== undefined);

  // --- Equal mode state ---
  const [checkedIds, setCheckedIds] = useState<Set<string>>(
    () => new Set(itemsWithPrice.map((it) => it.id)),
  );
  const allChecked = checkedIds.size === itemsWithPrice.length;
  const selectedTotal = itemsWithPrice
    .filter((it) => checkedIds.has(it.id))
    .reduce((s, it) => s + (it.total_price ?? 0), 0);
  const splitBase = itemsWithPrice.length > 0 ? selectedTotal : total;
  const n = users.length + 1;
  const share = users.length === 0 ? splitBase : Math.round((splitBase / n) * 100) / 100;

  function toggleAll() {
    if (allChecked) setCheckedIds(new Set());
    else setCheckedIds(new Set(itemsWithPrice.map((it) => it.id)));
  }

  function toggleItem(id: string) {
    setCheckedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  // --- Assign mode helpers ---
  function toggleAssignment(username: string, itemId: string) {
    setAssignments((prev) => {
      const next = { ...prev };
      // Remove from any other person first (exclusive assignment)
      for (const other of Object.keys(next)) {
        if (other !== username) {
          const s = new Set(next[other]);
          s.delete(itemId);
          next[other] = s;
        }
      }
      // Toggle for this person
      const s = new Set(next[username] ?? []);
      if (s.has(itemId)) s.delete(itemId);
      else s.add(itemId);
      next[username] = s;
      return next;
    });
  }

  function getPersonTotal(username: string): number {
    return itemsWithPrice
      .filter((it) => assignments[username]?.has(it.id))
      .reduce((s, it) => s + (it.total_price ?? 0), 0);
  }

  function getAssignedToOthers(username: string): Set<string> {
    const s = new Set<string>();
    for (const [u, ids] of Object.entries(assignments)) {
      if (u !== username) ids.forEach((id) => s.add(id));
    }
    return s;
  }

  // --- User management ---
  function selectFriend(f: { user_id: string; username: string; name: string | null }) {
    setUsers((prev) => [...prev, { id: f.user_id, username: f.username, name: f.name }]);
    setRawInput("");
    setShowDropdown(false);
    inputRef.current?.focus();
  }

  function removeUser(username: string) {
    setUsers((prev) => prev.filter((u) => u.username !== username));
    setAssignments((prev) => {
      const next = { ...prev };
      delete next[username];
      return next;
    });
  }

  async function addUser() {
    const username = rawInput.trim().toLowerCase();
    if (!username) return;
    if (users.some((u) => u.username === username)) {
      setLookupError("Already added");
      return;
    }
    const friend = friendsList.find((f) => f.username === username);
    if (friend) {
      selectFriend(friend);
      return;
    }
    setLookupError(null);
    setIsLooking(true);
    try {
      const found = await api.getUserByUsername(username);
      setUsers((prev) => [...prev, { id: found.id, username: found.username, name: found.name }]);
      setRawInput("");
      inputRef.current?.focus();
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setLookupError(`"${username}" not found`);
      } else {
        setLookupError("Lookup failed. Try again.");
      }
    } finally {
      setIsLooking(false);
    }
  }

  // --- Mutations ---
  const sendFriendMutation = useMutation({
    mutationFn: async (nonFriends: NonFriendInfo[]) => {
      for (const nf of nonFriends) {
        await friendsApi.sendRequest({
          username: nf.username,
          deferred_split: {
            bill_id: billId,
            amount: nf.amount,
            bill_item_ids: nf.bill_item_ids ?? undefined,
          },
        });
      }
    },
    onSettled: () => {
      onSuccess();
      onClose();
    },
  });

  const sendMutation = useMutation({
    mutationFn: () => {
      if (mode === "assign") {
        const assignmentsList: RecipientAssignment[] = users.map((u) => ({
          username: u.username,
          bill_item_ids: Array.from(assignments[u.username] ?? new Set<string>()),
        }));
        return api.create(billId, [], { assignments: assignmentsList });
      }
      const usernames = users.map((u) => u.username);
      if (itemsWithPrice.length > 0) {
        return api.create(billId, usernames, { billItemIds: Array.from(checkedIds) });
      }
      return api.create(billId, usernames, { totalToSplit: splitBase });
    },
    onSuccess: (result) => {
      if (result.non_friends.length > 0) {
        setNonFriendQueue(result.non_friends);
      } else {
        onSuccess();
        onClose();
      }
    },
  });

  const sendError =
    sendMutation.error instanceof ApiError
      ? sendMutation.error.detail
      : sendMutation.error
        ? "Failed to send requests."
        : null;

  // Disabled logic
  const assignModeHasUnassigned =
    mode === "assign" && users.some((u) => !(assignments[u.username]?.size ?? 0));
  const sendDisabled =
    users.length === 0 ||
    sendMutation.isPending ||
    (mode === "equal" && itemsWithPrice.length > 0 && checkedIds.size === 0) ||
    (mode === "assign" && assignModeHasUnassigned);

  // --- Non-friend confirmation screen ---
  if (nonFriendQueue !== null) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
        <div className="bg-white rounded-2xl shadow-xl w-full sm:max-w-md mx-4 p-6 space-y-4">
          <h2 className="text-lg font-semibold">Not in your friends list</h2>
          <p className="text-sm text-slate-600">
            {nonFriendQueue.length === 1 ? "This user is" : "These users are"} not in your friends
            list. Send a friend request? Once accepted, the split request will be sent automatically.
          </p>
          <ul className="space-y-1.5 border border-slate-200 rounded p-3 bg-slate-50">
            {nonFriendQueue.map((nf) => (
              <li key={nf.username} className="flex justify-between text-sm">
                <span className="font-medium">@{nf.username}</span>
                <span className="font-mono text-slate-600">{nf.amount.toFixed(2)}</span>
              </li>
            ))}
          </ul>
          {sendFriendMutation.isError && (
            <p className="text-xs text-red-600">
              {sendFriendMutation.error instanceof ApiError
                ? sendFriendMutation.error.detail
                : "Failed to send some friend requests."}
            </p>
          )}
          <div className="flex gap-3 justify-end pt-1">
            <button
              type="button"
              onClick={() => { onSuccess(); onClose(); }}
              className="text-sm text-slate-600 hover:text-slate-900 px-3 py-2"
            >
              Skip
            </button>
            <button
              type="button"
              disabled={sendFriendMutation.isPending}
              onClick={() => sendFriendMutation.mutate(nonFriendQueue)}
              className="bg-slate-900 text-white text-sm rounded px-4 py-2 disabled:opacity-50"
            >
              {sendFriendMutation.isPending
                ? "Sending…"
                : `Send friend request${nonFriendQueue.length !== 1 ? "s" : ""}`}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/50"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-t-2xl sm:rounded-2xl shadow-xl w-full sm:max-w-lg sm:mx-4 p-6 space-y-5 max-h-[92vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold">Split this bill</h2>
            {merchant && <p className="text-sm text-slate-500 mt-0.5">{merchant}</p>}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 text-xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        {/* Mode toggle — only when items have prices */}
        {itemsWithPrice.length > 0 && (
          <div className="flex rounded-lg border border-slate-200 p-0.5 bg-slate-50 text-sm w-fit">
            <button
              type="button"
              onClick={() => setMode("equal")}
              className={`px-3 py-1.5 rounded-md font-medium transition-colors ${
                mode === "equal"
                  ? "bg-white shadow-sm text-slate-900"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              Equal split
            </button>
            <button
              type="button"
              onClick={() => setMode("assign")}
              className={`px-3 py-1.5 rounded-md font-medium transition-colors ${
                mode === "assign"
                  ? "bg-white shadow-sm text-slate-900"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              Assign items
            </button>
          </div>
        )}

        {/* Equal mode: item selection */}
        {mode === "equal" && itemsWithPrice.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-slate-700">Select items to split</span>
              <button
                type="button"
                onClick={toggleAll}
                className="text-xs text-slate-500 hover:text-slate-800 underline"
              >
                {allChecked ? "Deselect all" : "Select all"}
              </button>
            </div>
            <ul className="divide-y divide-slate-100 border border-slate-200 rounded max-h-40 overflow-y-auto">
              {itemsWithPrice.map((item) => (
                <li key={item.id} className="flex items-center gap-2 px-3 py-2 text-sm">
                  <input
                    type="checkbox"
                    id={`item-${item.id}`}
                    checked={checkedIds.has(item.id)}
                    onChange={() => toggleItem(item.id)}
                    className="shrink-0"
                  />
                  <label htmlFor={`item-${item.id}`} className="flex-1 cursor-pointer text-slate-800">
                    {item.name}
                  </label>
                  <span className="font-mono text-slate-500 text-xs">
                    {(item.total_price ?? 0).toFixed(2)}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Username input with friends dropdown */}
        <div className="space-y-1">
          <label className="block text-sm font-medium text-slate-700">
            {mode === "assign" ? "Add people, then assign their items below" : "Add people to split with"}
          </label>
          <div className="relative">
            <div className="flex gap-2">
              <input
                ref={inputRef}
                type="text"
                placeholder={friendsList.length > 0 ? "Search friends or type username…" : "username"}
                value={rawInput}
                onChange={(e) => {
                  setRawInput(e.target.value.toLowerCase().replace(/[^a-z0-9]/g, ""));
                  setShowDropdown(true);
                }}
                onFocus={() => setShowDropdown(true)}
                onBlur={() => setTimeout(() => setShowDropdown(false), 150)}
                onKeyDown={(e) => e.key === "Enter" && void addUser()}
                className="flex-1 border border-slate-300 rounded px-3 py-2 text-sm"
                disabled={isLooking}
                autoFocus={itemsWithPrice.length === 0}
              />
              <button
                type="button"
                onClick={() => void addUser()}
                disabled={!rawInput.trim() || isLooking}
                className="bg-slate-800 text-white text-sm rounded px-4 py-2 disabled:opacity-50"
              >
                {isLooking ? "…" : "Add"}
              </button>
            </div>

            {/* Friends dropdown */}
            {showDropdown && suggestions.length > 0 && (
              <ul className="absolute z-10 left-0 right-12 mt-1 bg-white border border-slate-200 rounded shadow-lg max-h-48 overflow-y-auto text-sm">
                {suggestions.map((f) => (
                  <li key={f.user_id}>
                    <button
                      type="button"
                      onMouseDown={(e) => e.preventDefault()}
                      onClick={() => selectFriend(f)}
                      className="w-full text-left px-3 py-2 hover:bg-slate-50 flex items-center gap-2"
                    >
                      <span className="font-medium">@{f.username}</span>
                      {f.name && <span className="text-slate-500 text-xs">{f.name}</span>}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          {lookupError && <p className="text-xs text-red-600">{lookupError}</p>}
        </div>

        {/* Added users list (equal mode shows share; assign mode shows person total) */}
        {users.length > 0 && mode === "equal" && (
          <ul className="divide-y divide-slate-100 border border-slate-200 rounded text-sm">
            {users.map((u) => (
              <li key={u.id} className="flex items-center justify-between px-3 py-2">
                <span>
                  <span className="font-medium">@{u.username}</span>
                  {u.name && <span className="ml-1.5 text-slate-500">{u.name}</span>}
                  {friendsList.some((f) => f.user_id === u.id) && (
                    <span className="ml-1.5 text-xs text-emerald-600">friend</span>
                  )}
                </span>
                <div className="flex items-center gap-3">
                  <span className="font-mono text-slate-700">{share.toFixed(2)}</span>
                  <button
                    type="button"
                    onClick={() => removeUser(u.username)}
                    className="text-slate-400 hover:text-red-600"
                    aria-label={`Remove ${u.username}`}
                  >
                    ×
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}

        {/* Assign mode: per-person item cards */}
        {mode === "assign" && users.length > 0 && (
          <div className="space-y-3">
            <p className="text-sm font-medium text-slate-700">Assign items to each person</p>
            {users.map((u) => {
              const assignedToOthers = getAssignedToOthers(u.username);
              const personTotal = getPersonTotal(u.username);
              return (
                <div key={u.id} className="border border-slate-200 rounded-xl overflow-hidden">
                  <div className="flex items-center justify-between px-3 py-2 bg-slate-50">
                    <span className="text-sm font-medium">
                      @{u.username}
                      {u.name && <span className="ml-1.5 text-slate-400 font-normal text-xs">{u.name}</span>}
                      {friendsList.some((f) => f.user_id === u.id) && (
                        <span className="ml-1.5 text-xs text-emerald-600">friend</span>
                      )}
                    </span>
                    <div className="flex items-center gap-3">
                      <span className={`font-mono text-sm ${personTotal > 0 ? "text-slate-700 font-medium" : "text-slate-400"}`}>
                        {personTotal > 0 ? personTotal.toFixed(2) : "—"}
                      </span>
                      <button
                        type="button"
                        onClick={() => removeUser(u.username)}
                        className="text-slate-400 hover:text-red-600 text-base"
                        aria-label={`Remove ${u.username}`}
                      >
                        ×
                      </button>
                    </div>
                  </div>
                  <ul className="divide-y divide-slate-100 max-h-44 overflow-y-auto">
                    {itemsWithPrice.map((item) => {
                      const isChecked = assignments[u.username]?.has(item.id) ?? false;
                      const isDisabled = assignedToOthers.has(item.id);
                      return (
                        <li key={item.id} className="flex items-center gap-2 px-3 py-2 text-sm">
                          <input
                            type="checkbox"
                            id={`assign-${u.username}-${item.id}`}
                            checked={isChecked}
                            disabled={isDisabled}
                            onChange={() => toggleAssignment(u.username, item.id)}
                            className="shrink-0"
                          />
                          <label
                            htmlFor={`assign-${u.username}-${item.id}`}
                            className={`flex-1 ${
                              isDisabled
                                ? "text-slate-400 line-through cursor-not-allowed"
                                : "text-slate-800 cursor-pointer"
                            }`}
                          >
                            {item.name}
                          </label>
                          <span className={`font-mono text-xs ${isDisabled ? "text-slate-300" : "text-slate-500"}`}>
                            {(item.total_price ?? 0).toFixed(2)}
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              );
            })}
          </div>
        )}

        {/* Amount preview */}
        {mode === "equal" && (
          <div className="rounded bg-slate-50 border border-slate-200 px-4 py-3 text-sm space-y-1">
            <div className="flex justify-between">
              <span className="text-slate-600">
                {itemsWithPrice.length > 0 ? "Selected items total" : "Bill total"}
              </span>
              <span className="font-mono font-medium">{splitBase.toFixed(2)}</span>
            </div>
            {users.length > 0 && (
              <div className="flex justify-between">
                <span className="text-slate-600">Split {n} ways</span>
                <span className="font-mono font-medium">{share.toFixed(2)} each</span>
              </div>
            )}
            {users.length > 0 && (
              <div className="flex justify-between text-emerald-700 font-medium border-t border-slate-200 pt-1 mt-1">
                <span>Your portion</span>
                <span className="font-mono">{share.toFixed(2)}</span>
              </div>
            )}
          </div>
        )}

        {mode === "assign" && users.length > 0 && (
          <div className="rounded bg-slate-50 border border-slate-200 px-4 py-3 text-sm space-y-1.5">
            {users.map((u) => {
              const amt = getPersonTotal(u.username);
              return (
                <div key={u.username} className="flex justify-between">
                  <span className="text-slate-600">@{u.username}</span>
                  <span className={`font-mono font-medium ${amt > 0 ? "text-slate-800" : "text-slate-400"}`}>
                    {amt > 0 ? amt.toFixed(2) : "nothing assigned"}
                  </span>
                </div>
              );
            })}
            {/* Unassigned items = your portion */}
            {(() => {
              const allAssignedIds = new Set(
                Object.values(assignments).flatMap((s) => Array.from(s)),
              );
              const yourTotal = itemsWithPrice
                .filter((it) => !allAssignedIds.has(it.id))
                .reduce((s, it) => s + (it.total_price ?? 0), 0);
              return (
                <div className="flex justify-between text-emerald-700 font-medium border-t border-slate-200 pt-1 mt-1">
                  <span>Your portion</span>
                  <span className="font-mono">
                    {yourTotal > 0 ? yourTotal.toFixed(2) : "nothing"}
                  </span>
                </div>
              );
            })()}
          </div>
        )}

        {sendError && <p className="text-sm text-red-600">{sendError}</p>}
        {assignModeHasUnassigned && (
          <p className="text-xs text-amber-600">
            Each person must have at least one item assigned before sending.
          </p>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-1">
          <button
            type="button"
            onClick={onClose}
            className="text-sm text-slate-600 hover:text-slate-900 px-3 py-2"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={sendDisabled}
            onClick={() => sendMutation.mutate()}
            className="bg-slate-900 text-white text-sm rounded px-4 py-2 disabled:opacity-50"
          >
            {sendMutation.isPending
              ? "Sending…"
              : `Send ${users.length} request${users.length !== 1 ? "s" : ""}`}
          </button>
        </div>
      </div>
    </div>
  );
}
