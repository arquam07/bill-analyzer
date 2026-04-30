import { useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { splitRequests as api } from "~/api/endpoints";
import { ApiError } from "~/api/fetcher";
import type { BillItemResponse, UserPublicResponse } from "~/api/types";

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

export function SplitModal({ billId, total, merchant, items, onClose, onSuccess }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [rawInput, setRawInput] = useState("");
  const [users, setUsers] = useState<AddedUser[]>([]);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [isLooking, setIsLooking] = useState(false);

  // Item selection — default all checked
  const itemsWithPrice = items.filter((it) => it.total_price !== null && it.total_price !== undefined);
  const [checkedIds, setCheckedIds] = useState<Set<string>>(
    () => new Set(itemsWithPrice.map((it) => it.id)),
  );

  const allChecked = checkedIds.size === itemsWithPrice.length;
  const selectedTotal = itemsWithPrice
    .filter((it) => checkedIds.has(it.id))
    .reduce((s, it) => s + (it.total_price ?? 0), 0);

  // If no items have prices, fall back to bill total
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

  async function addUser() {
    const username = rawInput.trim().toLowerCase();
    if (!username) return;
    if (users.some((u) => u.username === username)) {
      setLookupError("Already added");
      return;
    }
    setLookupError(null);
    setIsLooking(true);
    try {
      const found: UserPublicResponse = await api.getUserByUsername(username);
      setUsers((prev) => [
        ...prev,
        { id: found.id, username: found.username, name: found.name },
      ]);
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

  const sendMutation = useMutation({
    mutationFn: () =>
      api.create(billId, users.map((u) => u.username), splitBase),
    onSuccess: () => {
      onSuccess();
      onClose();
    },
  });

  const sendError =
    sendMutation.error instanceof ApiError
      ? sendMutation.error.detail
      : sendMutation.error
        ? "Failed to send requests."
        : null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 p-6 space-y-5 max-h-[90vh] overflow-y-auto">
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

        {/* Item selection */}
        {itemsWithPrice.length > 0 && (
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
                  <label
                    htmlFor={`item-${item.id}`}
                    className="flex-1 cursor-pointer text-slate-800"
                  >
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

        {/* Username input */}
        <div className="space-y-1">
          <label className="block text-sm font-medium text-slate-700">
            Add people to split with
          </label>
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              placeholder="username"
              value={rawInput}
              onChange={(e) =>
                setRawInput(e.target.value.toLowerCase().replace(/[^a-z0-9]/g, ""))
              }
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
          {lookupError && <p className="text-xs text-red-600">{lookupError}</p>}
        </div>

        {/* Added users list */}
        {users.length > 0 && (
          <ul className="divide-y divide-slate-100 border border-slate-200 rounded text-sm">
            {users.map((u) => (
              <li key={u.id} className="flex items-center justify-between px-3 py-2">
                <span>
                  <span className="font-medium">@{u.username}</span>
                  {u.name && <span className="ml-1.5 text-slate-500">{u.name}</span>}
                </span>
                <div className="flex items-center gap-3">
                  <span className="font-mono text-slate-700">{share.toFixed(2)}</span>
                  <button
                    type="button"
                    onClick={() => setUsers((prev) => prev.filter((x) => x.id !== u.id))}
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

        {/* Amount preview */}
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

        {sendError && <p className="text-sm text-red-600">{sendError}</p>}

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
            disabled={users.length === 0 || sendMutation.isPending || (itemsWithPrice.length > 0 && checkedIds.size === 0)}
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
