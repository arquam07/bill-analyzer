import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { bills as billsApi } from "~/api/endpoints";
import { ApiError } from "~/api/fetcher";
import { useAuth } from "~/auth/AuthContext";
import { SplitModal } from "~/features/splits/SplitModal";
import type {
  BillItemCreateRequest,
  BillItemResponse,
  BillItemUpdateRequest,
  BillResponse,
  BillUpdateRequest,
} from "~/api/types";
import { CURRENCIES } from "~/features/insights/currencies";

const EXTRACTION_MESSAGES = [
  "Reading receipt…",
  "Detecting line items…",
  "Identifying merchant…",
  "Parsing totals…",
  "Almost there…",
];

function ExtractionButton({
  isPending,
  label,
  reextract,
  onClick,
  className,
}: {
  isPending: boolean;
  label: string;
  reextract?: boolean;
  onClick: () => void;
  className: string;
}) {
  const [msgIdx, setMsgIdx] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (isPending) {
      setMsgIdx(0);
      intervalRef.current = setInterval(
        () => setMsgIdx((i) => (i + 1) % EXTRACTION_MESSAGES.length),
        10_000,
      );
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
      setMsgIdx(0);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isPending]);

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={isPending}
      className={className}
    >
      {isPending ? (
        <span className="flex items-center gap-2">
          <svg
            className="animate-spin h-4 w-4 shrink-0"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
          {EXTRACTION_MESSAGES[msgIdx]}
        </span>
      ) : reextract ? (
        "Re-extract"
      ) : (
        label
      )}
    </button>
  );
}

function asNumber(s: string): number | null {
  if (s.trim() === "") return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

const BILL_CATEGORIES = [
  "grocery",
  "pharmacy",
  "food",
  "clothes",
  "transport",
  "entertainment",
  "household",
  "other",
] as const;

function BillFields({
  bill,
  locked,
  onSave,
}: {
  bill: BillResponse;
  locked: boolean;
  onSave: (patch: BillUpdateRequest) => void;
}) {
  const [merchant, setMerchant] = useState(bill.merchant ?? "");
  const [total, setTotal] = useState(bill.total !== null ? String(bill.total) : "");
  const [currency, setCurrency] = useState(bill.currency ?? "");
  const [billedAt, setBilledAt] = useState(bill.billed_at ?? "");
  const [category, setCategory] = useState(bill.category ?? "");

  useEffect(() => {
    setMerchant(bill.merchant ?? "");
    setTotal(bill.total !== null && bill.total !== undefined ? String(bill.total) : "");
    setCurrency(bill.currency ?? "");
    setBilledAt(bill.billed_at ?? "");
    setCategory(bill.category ?? "");
  }, [bill]);

  function commitIfChanged(field: keyof BillUpdateRequest, current: unknown, original: unknown) {
    if (current === original) return;
    onSave({ [field]: current } as BillUpdateRequest);
  }

  const inputCls = "mt-1 w-full border border-slate-300 rounded-lg px-3 py-3 text-base disabled:bg-slate-50";

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      <label className="text-sm">
        <span className="text-slate-600 font-medium">Merchant</span>
        <input
          type="text"
          disabled={locked}
          value={merchant}
          onChange={(e) => setMerchant(e.target.value)}
          onBlur={() => commitIfChanged("merchant", merchant || null, bill.merchant ?? null)}
          className={inputCls}
        />
      </label>
      <label className="text-sm">
        <span className="text-slate-600 font-medium">Total</span>
        <input
          type="number"
          step="0.01"
          disabled={locked}
          value={total}
          onChange={(e) => setTotal(e.target.value)}
          onBlur={() => commitIfChanged("total", asNumber(total), bill.total ?? null)}
          className={inputCls}
        />
      </label>
      <label className="text-sm">
        <span className="text-slate-600 font-medium">Currency</span>
        <select
          disabled={locked}
          value={currency}
          onChange={(e) => {
            setCurrency(e.target.value);
            onSave({ currency: e.target.value || null });
          }}
          className={inputCls}
        >
          <option value="">— select —</option>
          {CURRENCIES.map((c) => (
            <option key={c.code} value={c.code}>
              {c.code} — {c.name}
            </option>
          ))}
        </select>
      </label>
      <label className="text-sm">
        <span className="text-slate-600 font-medium">Billed at</span>
        <input
          type="date"
          disabled={locked}
          value={billedAt}
          onChange={(e) => setBilledAt(e.target.value)}
          onBlur={() => commitIfChanged("billed_at", billedAt || null, bill.billed_at ?? null)}
          className={inputCls}
        />
      </label>
      <label className="text-sm md:col-span-2">
        <span className="text-slate-600 font-medium">Category</span>
        <select
          disabled={locked}
          value={category}
          onChange={(e) => {
            const next = e.target.value;
            setCategory(next);
            commitIfChanged("category", next || null, bill.category ?? null);
          }}
          className={`${inputCls} bg-white`}
        >
          <option value="">(uncategorized)</option>
          {BILL_CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}

function useItemEditor(
  item: BillItemResponse,
  onUpdate: (patch: BillItemUpdateRequest) => void,
) {
  const [name, setName] = useState(item.name);
  const [qty, setQty] = useState(item.quantity !== null && item.quantity !== undefined ? String(item.quantity) : "");
  const [unit, setUnit] = useState(item.unit_price !== null && item.unit_price !== undefined ? String(item.unit_price) : "");
  const [total, setTotal] = useState(item.total_price !== null && item.total_price !== undefined ? String(item.total_price) : "");
  const [category, setCategory] = useState(item.category ?? "");

  useEffect(() => {
    setName(item.name);
    setQty(item.quantity !== null && item.quantity !== undefined ? String(item.quantity) : "");
    setUnit(item.unit_price !== null && item.unit_price !== undefined ? String(item.unit_price) : "");
    setTotal(item.total_price !== null && item.total_price !== undefined ? String(item.total_price) : "");
    setCategory(item.category ?? "");
  }, [item]);

  const commitName = () => name !== item.name && onUpdate({ name });
  const commitQty = () => { const v = asNumber(qty); if (v !== (item.quantity ?? null)) onUpdate({ quantity: v }); };
  const commitUnit = () => { const v = asNumber(unit); if (v !== (item.unit_price ?? null)) onUpdate({ unit_price: v }); };
  const commitTotal = () => { const v = asNumber(total); if (v !== (item.total_price ?? null)) onUpdate({ total_price: v }); };
  const commitCategory = () => category !== (item.category ?? "") && onUpdate({ category: category || null });

  return {
    name, setName, commitName,
    qty, setQty, commitQty,
    unit, setUnit, commitUnit,
    total, setTotal, commitTotal,
    category, setCategory, commitCategory,
  };
}

function ItemRow({
  item,
  locked,
  onUpdate,
  onDelete,
}: {
  item: BillItemResponse;
  locked: boolean;
  onUpdate: (patch: BillItemUpdateRequest) => void;
  onDelete: () => void;
}) {
  const ed = useItemEditor(item, onUpdate);

  return (
    <tr className="border-t border-slate-200">
      <td className="px-2 py-1">
        <input
          type="text"
          disabled={locked}
          value={ed.name}
          onChange={(e) => ed.setName(e.target.value)}
          onBlur={ed.commitName}
          className="w-full px-2 py-1 border border-transparent hover:border-slate-300 rounded disabled:bg-transparent"
        />
      </td>
      <td className="px-2 py-1 w-20">
        <input
          type="number"
          step="0.001"
          disabled={locked}
          value={ed.qty}
          onChange={(e) => ed.setQty(e.target.value)}
          onBlur={ed.commitQty}
          className="w-full px-2 py-1 border border-transparent hover:border-slate-300 rounded text-right disabled:bg-transparent"
        />
      </td>
      <td className="px-2 py-1 w-24">
        <input
          type="number"
          step="0.01"
          disabled={locked}
          value={ed.unit}
          onChange={(e) => ed.setUnit(e.target.value)}
          onBlur={ed.commitUnit}
          className="w-full px-2 py-1 border border-transparent hover:border-slate-300 rounded text-right disabled:bg-transparent"
        />
      </td>
      <td className="px-2 py-1 w-24">
        <input
          type="number"
          step="0.01"
          disabled={locked}
          value={ed.total}
          onChange={(e) => ed.setTotal(e.target.value)}
          onBlur={ed.commitTotal}
          className="w-full px-2 py-1 border border-transparent hover:border-slate-300 rounded text-right disabled:bg-transparent"
        />
      </td>
      <td className="px-2 py-1 w-28">
        <input
          type="text"
          disabled={locked}
          value={ed.category}
          onChange={(e) => ed.setCategory(e.target.value)}
          onBlur={ed.commitCategory}
          className="w-full px-2 py-1 border border-transparent hover:border-slate-300 rounded disabled:bg-transparent"
        />
      </td>
      <td className="px-2 py-1 w-12 text-right">
        {!locked && (
          <button
            type="button"
            onClick={onDelete}
            className="text-red-500 hover:text-red-700 text-lg leading-none w-8 h-8 flex items-center justify-center"
            aria-label={`Delete ${item.name}`}
          >
            ×
          </button>
        )}
      </td>
    </tr>
  );
}

function AddItemRow({ onAdd }: { onAdd: (body: BillItemCreateRequest) => void }) {
  const [name, setName] = useState("");
  const [total, setTotal] = useState("");

  function submit() {
    if (!name.trim()) return;
    onAdd({ name: name.trim(), total_price: asNumber(total) });
    setName("");
    setTotal("");
  }

  return (
    <tr className="border-t border-slate-200 bg-slate-50">
      <td className="px-2 py-1">
        <input
          type="text"
          placeholder="New item…"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full px-2 py-1 border border-slate-300 rounded"
        />
      </td>
      <td colSpan={2}></td>
      <td className="px-2 py-1">
        <input
          type="number"
          step="0.01"
          placeholder="Price"
          value={total}
          onChange={(e) => setTotal(e.target.value)}
          className="w-full px-2 py-1 border border-slate-300 rounded text-right"
        />
      </td>
      <td colSpan={2} className="px-2 py-1">
        <button
          type="button"
          onClick={submit}
          disabled={!name.trim()}
          className="w-full bg-slate-800 text-white text-sm rounded px-2 py-1 disabled:opacity-50"
        >
          Add
        </button>
      </td>
    </tr>
  );
}

function ItemCard({
  item,
  locked,
  onUpdate,
  onDelete,
}: {
  item: BillItemResponse;
  locked: boolean;
  onUpdate: (patch: BillItemUpdateRequest) => void;
  onDelete: () => void;
}) {
  const ed = useItemEditor(item, onUpdate);

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-3 space-y-2">
      <div className="flex items-center gap-2">
        <input
          type="text"
          disabled={locked}
          value={ed.name}
          onChange={(e) => ed.setName(e.target.value)}
          onBlur={ed.commitName}
          placeholder="Item name"
          className="flex-1 text-sm font-medium border border-transparent focus:border-slate-300 rounded-lg px-2 py-1.5 disabled:bg-transparent"
        />
        {!locked && (
          <button
            type="button"
            onClick={onDelete}
            className="shrink-0 text-slate-400 hover:text-red-600 w-8 h-8 flex items-center justify-center text-xl leading-none"
            aria-label={`Delete ${item.name}`}
          >
            ×
          </button>
        )}
      </div>
      <div className="grid grid-cols-3 gap-2">
        <label className="space-y-0.5">
          <span className="text-xs text-slate-500 block">Qty</span>
          <input
            type="number"
            step="0.001"
            disabled={locked}
            value={ed.qty}
            onChange={(e) => ed.setQty(e.target.value)}
            onBlur={ed.commitQty}
            className="w-full border border-slate-200 rounded-lg px-2 py-1.5 text-sm text-right disabled:bg-transparent"
          />
        </label>
        <label className="space-y-0.5">
          <span className="text-xs text-slate-500 block">Unit $</span>
          <input
            type="number"
            step="0.01"
            disabled={locked}
            value={ed.unit}
            onChange={(e) => ed.setUnit(e.target.value)}
            onBlur={ed.commitUnit}
            className="w-full border border-slate-200 rounded-lg px-2 py-1.5 text-sm text-right disabled:bg-transparent"
          />
        </label>
        <label className="space-y-0.5">
          <span className="text-xs text-slate-500 block">Total $</span>
          <input
            type="number"
            step="0.01"
            disabled={locked}
            value={ed.total}
            onChange={(e) => ed.setTotal(e.target.value)}
            onBlur={ed.commitTotal}
            className="w-full border border-slate-200 rounded-lg px-2 py-1.5 text-sm text-right disabled:bg-transparent"
          />
        </label>
      </div>
      <label className="flex items-center gap-2 text-xs text-slate-500">
        <span className="shrink-0">Category</span>
        <input
          type="text"
          disabled={locked}
          value={ed.category}
          onChange={(e) => ed.setCategory(e.target.value)}
          onBlur={ed.commitCategory}
          className="flex-1 border border-slate-200 rounded-lg px-2 py-1.5 text-sm text-slate-800 disabled:bg-transparent"
        />
      </label>
    </div>
  );
}

function AddItemCard({ onAdd }: { onAdd: (body: BillItemCreateRequest) => void }) {
  const [name, setName] = useState("");
  const [total, setTotal] = useState("");

  function submit() {
    if (!name.trim()) return;
    onAdd({ name: name.trim(), total_price: asNumber(total) });
    setName("");
    setTotal("");
  }

  return (
    <div className="border border-dashed border-slate-300 rounded-xl p-3 space-y-2">
      <input
        type="text"
        placeholder="Item name…"
        value={name}
        onChange={(e) => setName(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && submit()}
        className="w-full border border-slate-200 rounded-lg px-3 py-2.5 text-sm"
      />
      <div className="flex gap-2">
        <input
          type="number"
          step="0.01"
          placeholder="Price"
          value={total}
          onChange={(e) => setTotal(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          className="flex-1 border border-slate-200 rounded-lg px-3 py-2.5 text-sm text-right"
        />
        <button
          type="button"
          onClick={submit}
          disabled={!name.trim()}
          className="bg-slate-800 text-white text-sm rounded-lg px-4 py-2.5 disabled:opacity-50"
        >
          Add
        </button>
      </div>
    </div>
  );
}

function BillDetail() {
  const { billId } = Route.useParams();
  const { user, isLoading: authLoading } = useAuth();
  const navigate = useNavigate();
  const qc = useQueryClient();

  useEffect(() => {
    if (!authLoading && !user) void navigate({ to: "/login" });
  }, [authLoading, user, navigate]);

  const [showSplit, setShowSplit] = useState(false);

  const billQuery = useQuery({
    queryKey: ["bills", billId],
    queryFn: () => billsApi.get(billId),
    enabled: Boolean(user),
  });

  function setBill(updated: BillResponse) {
    qc.setQueryData(["bills", billId], updated);
    void qc.invalidateQueries({ queryKey: ["bills"] });
  }

  function setBillAndRefreshInsights(updated: BillResponse) {
    setBill(updated);
    void qc.invalidateQueries({ queryKey: ["insights"] });
  }

  const patchBill = useMutation({
    mutationFn: (body: BillUpdateRequest) => billsApi.patch(billId, body),
    onSuccess: setBill,
  });
  const extract = useMutation({
    mutationFn: () => billsApi.extract(billId),
    onSuccess: setBillAndRefreshInsights,
  });
  const finalize = useMutation({
    mutationFn: () => billsApi.finalize(billId),
    onSuccess: setBillAndRefreshInsights,
  });
  const addItem = useMutation({
    mutationFn: (body: BillItemCreateRequest) => billsApi.addItem(billId, body),
    onSuccess: setBill,
  });
  const updateItem = useMutation({
    mutationFn: (args: { itemId: string; body: BillItemUpdateRequest }) =>
      billsApi.updateItem(billId, args.itemId, args.body),
    onSuccess: setBill,
  });
  const deleteItem = useMutation({
    mutationFn: (itemId: string) => billsApi.deleteItem(billId, itemId),
    onSuccess: setBill,
  });

  if (authLoading || !user) return <p className="text-slate-500">Loading…</p>;
  if (billQuery.isLoading) return <p className="text-slate-500">Loading bill…</p>;
  if (billQuery.error) {
    const msg =
      billQuery.error instanceof ApiError ? billQuery.error.detail : "Error";
    return <p className="text-red-600">{msg}</p>;
  }
  if (!billQuery.data) return null;

  const bill = billQuery.data;
  const items: BillItemResponse[] = bill.items ?? [];
  const locked = bill.status === "reviewed";
  const hasImage = Boolean(bill.image_path);
  const apiBase = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";
  const imageUrl = hasImage ? `${apiBase}/storage/${bill.image_path}` : null;

  const lastError =
    patchBill.error ??
    extract.error ??
    finalize.error ??
    addItem.error ??
    updateItem.error ??
    deleteItem.error;

  return (
    <div className="space-y-4">
      {/* Header: stacks on mobile, row on desktop */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold truncate">
            {bill.merchant ?? <span className="text-slate-400">(unnamed bill)</span>}
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            <span className="font-medium capitalize">{bill.status}</span>
            {" · "}
            {new Date(bill.created_at).toLocaleDateString()}
          </p>
        </div>
        <div className="flex flex-wrap gap-2 shrink-0">
          {bill.total !== null && bill.total !== undefined && (
            <button
              type="button"
              onClick={() => setShowSplit(true)}
              className="bg-violet-700 text-white text-sm rounded-lg px-4 py-2.5 hover:bg-violet-800 font-medium"
            >
              Split bill
            </button>
          )}
          {bill.status === "uploaded" && hasImage && (
            <ExtractionButton
              isPending={extract.isPending}
              label="Run extraction"
              onClick={() => extract.mutate()}
              className="bg-slate-900 text-white text-sm rounded-lg px-4 py-2.5 disabled:opacity-60 font-medium"
            />
          )}
          {bill.status === "extracted" && (
            <>
              {hasImage && (
                <ExtractionButton
                  isPending={extract.isPending}
                  label="Re-extract"
                  reextract
                  onClick={() => extract.mutate()}
                  className="bg-white border border-slate-300 text-sm rounded-lg px-4 py-2.5 disabled:opacity-60"
                />
              )}
              <button
                type="button"
                onClick={() => finalize.mutate()}
                disabled={finalize.isPending}
                className="bg-emerald-700 text-white text-sm rounded-lg px-4 py-2.5 disabled:opacity-60 font-medium"
              >
                {finalize.isPending ? "Finalizing…" : "Finalize"}
              </button>
            </>
          )}
        </div>
      </div>

      {locked && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          This bill is finalized. Editing is locked.
        </div>
      )}

      {lastError && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {lastError instanceof ApiError ? lastError.detail : "Something went wrong."}
        </div>
      )}

      <section className="bg-white border border-slate-200 rounded-2xl p-4 space-y-3">
        <h2 className="font-semibold text-slate-800">Details</h2>
        <BillFields
          bill={bill}
          locked={locked}
          onSave={(patch) => patchBill.mutate(patch)}
        />
      </section>

      <section className="bg-white border border-slate-200 rounded-2xl p-4 space-y-3">
        <h2 className="font-semibold text-slate-800">Items</h2>
        {items.length === 0 ? (
          <p className="text-sm text-slate-500">
            {bill.status === "uploaded"
              ? "Run extraction to detect items, or add them manually."
              : "No items yet."}
          </p>
        ) : (
          <>
            {/* Desktop: table */}
            <div className="hidden sm:block overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-2 py-1 font-medium">Name</th>
                    <th className="px-2 py-1 font-medium text-right">Qty</th>
                    <th className="px-2 py-1 font-medium text-right">Unit</th>
                    <th className="px-2 py-1 font-medium text-right">Total</th>
                    <th className="px-2 py-1 font-medium">Category</th>
                    <th className="px-2 py-1"></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <ItemRow
                      key={item.id}
                      item={item}
                      locked={locked}
                      onUpdate={(body) => updateItem.mutate({ itemId: item.id, body })}
                      onDelete={() => deleteItem.mutate(item.id)}
                    />
                  ))}
                  {!locked && <AddItemRow onAdd={(body) => addItem.mutate(body)} />}
                </tbody>
              </table>
            </div>
            {/* Mobile: cards */}
            <div className="sm:hidden space-y-2">
              {items.map((item) => (
                <ItemCard
                  key={item.id}
                  item={item}
                  locked={locked}
                  onUpdate={(body) => updateItem.mutate({ itemId: item.id, body })}
                  onDelete={() => deleteItem.mutate(item.id)}
                />
              ))}
              {!locked && <AddItemCard onAdd={(body) => addItem.mutate(body)} />}
            </div>
          </>
        )}
        {items.length === 0 && !locked && (
          <>
            <div className="hidden sm:block">
              <table className="w-full text-sm mt-1">
                <tbody>
                  <AddItemRow onAdd={(body) => addItem.mutate(body)} />
                </tbody>
              </table>
            </div>
            <div className="sm:hidden">
              <AddItemCard onAdd={(body) => addItem.mutate(body)} />
            </div>
          </>
        )}
      </section>

      {bill.raw_ocr_text && (
        <details className="bg-white border border-slate-200 rounded-2xl p-4">
          <summary className="cursor-pointer text-sm text-slate-600 font-medium select-none">
            Raw OCR text
          </summary>
          <pre className="mt-2 text-xs whitespace-pre-wrap text-slate-700 leading-relaxed">
            {bill.raw_ocr_text}
          </pre>
        </details>
      )}

      {imageUrl && (
        <p className="text-xs text-slate-400 truncate px-1">image: {imageUrl}</p>
      )}

      {showSplit && bill.total !== null && bill.total !== undefined && (
        <SplitModal
          billId={bill.id}
          total={bill.total}
          merchant={bill.merchant ?? null}
          items={items}
          onClose={() => setShowSplit(false)}
          onSuccess={() => {
            void qc.invalidateQueries({ queryKey: ["split-requests"] });
          }}
        />
      )}
    </div>
  );
}

export const Route = createFileRoute("/bills/$billId")({
  component: BillDetail,
});
