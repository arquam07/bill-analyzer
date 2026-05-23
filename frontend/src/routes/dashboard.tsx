import { Link, createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { bills as billsApi } from "~/api/endpoints";
import { ApiError } from "~/api/fetcher";
import { useAuth } from "~/auth/AuthContext";
import {
  useBreakdown,
  useOverview,
  useTimeseries,
  useTopItems,
} from "~/features/insights/api";
import { BillsList } from "~/features/insights/BillsList";
import { SplitsTab } from "~/features/splits/SplitsTab";
import { BreakdownChart } from "~/features/insights/BreakdownChart";
import { ItemDetailDrawer } from "~/features/insights/ItemDetailDrawer";
import { KpiCards } from "~/features/insights/KpiCards";
import { SpendOverTimeChart } from "~/features/insights/SpendOverTimeChart";
import { TimeRangePicker } from "~/features/insights/TimeRangePicker";
import { TopItemsTable } from "~/features/insights/TopItemsTable";
import {
  DEFAULT_PRESET,
  PRESETS,
  pickGranularity,
  resolveRange,
  type Preset,
} from "~/features/insights/range";
import { CurrencyProvider, useCurrency } from "~/features/insights/CurrencyContext";
import { CURRENCIES } from "~/features/insights/currencies";
import type { ItemOrderBy } from "~/api/types";

type Tab = "insights" | "history" | "splits";
const TABS: readonly Tab[] = ["insights", "history", "splits"];

interface DashboardSearch {
  preset?: Preset;
  from?: string;
  to?: string;
  tab?: Tab;
  order_by?: ItemOrderBy;
}

function isPreset(v: unknown): v is Preset {
  return typeof v === "string" && (PRESETS as readonly string[]).includes(v);
}
function isTab(v: unknown): v is Tab {
  return (
    typeof v === "string" && (TABS as readonly string[]).includes(v)
  );
}
function isOrderBy(v: unknown): v is ItemOrderBy {
  return v === "spend" || v === "frequency";
}

function AddBillMenu() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    function onClickOutside(e: MouseEvent) {
      if (!wrapRef.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [open]);

  const uploadMutation = useMutation({
    mutationFn: (file: File) => billsApi.upload(file),
    onSuccess: async (bill) => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["bills"] }),
        qc.invalidateQueries({ queryKey: ["insights"] }),
      ]);
      void navigate({ to: "/bills/$billId", params: { billId: bill.id } });
    },
  });

  const createManual = useMutation({
    mutationFn: () => billsApi.createManual(),
    onSuccess: async (bill) => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["bills"] }),
        qc.invalidateQueries({ queryKey: ["insights"] }),
      ]);
      setOpen(false);
      void navigate({ to: "/bills/$billId", params: { billId: bill.id } });
    },
  });

  const busy = uploadMutation.isPending || createManual.isPending;

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    uploadMutation.mutate(file);
  }

  return (
    <div className="relative" ref={wrapRef}>
      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png"
        onChange={handleFileChange}
        className="sr-only"
      />
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        disabled={busy}
        className="bg-accent text-white text-sm font-semibold rounded-[9px] px-4 py-2.5 hover:bg-accent-deep hover:-translate-y-px hover:shadow-[0_8px_20px_rgba(224,83,61,.28)] disabled:opacity-60 transition-all duration-150 flex items-center gap-2"
      >
        <span className="text-base leading-none">＋</span>
        {uploadMutation.isPending ? "Uploading…" : createManual.isPending ? "Creating…" : "Add bill"}
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-52 rounded border border-slate-200 bg-card shadow-lg z-10">
          <button
            type="button"
            onClick={() => { setOpen(false); fileInputRef.current?.click(); }}
            className="block w-full text-left px-4 py-2 text-sm text-slate-800 hover:bg-slate-50"
          >
            Browse files
          </button>
          <Link
            to="/upload"
            onClick={() => setOpen(false)}
            className="block px-4 py-2 text-sm text-slate-800 hover:bg-slate-50 border-t border-slate-100"
          >
            Take a photo
          </Link>
          <button
            type="button"
            onClick={() => createManual.mutate()}
            className="block w-full text-left px-4 py-2 text-sm text-slate-800 hover:bg-slate-50 border-t border-slate-100"
          >
            Add bill manually
          </button>
          {(uploadMutation.error || createManual.error) && (
            <p className="px-4 py-2 text-xs text-red-600 border-t border-slate-100">
              {(uploadMutation.error ?? createManual.error) instanceof ApiError
                ? ((uploadMutation.error ?? createManual.error) as ApiError).detail
                : "Something went wrong."}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function CurrencyPicker() {
  const { currency, setCurrency } = useCurrency();
  return (
    <select
      value={currency}
      onChange={(e) => setCurrency(e.target.value)}
      className="font-medium text-[13.5px] text-slate-900 bg-card border border-slate-200 rounded-[10px] px-3.5 py-2 cursor-pointer focus:outline-none"
      aria-label="Display currency"
    >
      {CURRENCIES.map((c) => (
        <option key={c.code} value={c.code}>
          {c.code} — {c.name}
        </option>
      ))}
    </select>
  );
}

function DashboardPage() {
  const { user, isLoading: authLoading } = useAuth();
  const navigate = useNavigate();
  const search = Route.useSearch();
  const [selectedItem, setSelectedItem] = useState<{
    normalized_name: string;
    name: string;
  } | null>(null);

  useEffect(() => {
    if (!authLoading && !user) void navigate({ to: "/login" });
  }, [authLoading, user, navigate]);

  const preset = search.preset ?? DEFAULT_PRESET;
  const tab: Tab = search.tab ?? "insights";
  const orderBy: ItemOrderBy = search.order_by ?? "spend";

  const range = useMemo(
    () => resolveRange(preset, search.from, search.to),
    [preset, search.from, search.to],
  );
  const granularity = useMemo(() => pickGranularity(range), [range]);

  const enabled = Boolean(user) && tab === "insights";
  const splitsEnabled = Boolean(user) && tab === "splits";
  const overview = useOverview(range.from, range.to, enabled);
  const timeseries = useTimeseries(range.from, range.to, granularity, enabled);
  const categoryBreakdown = useBreakdown(range.from, range.to, "category", enabled);
  const merchantBreakdown = useBreakdown(range.from, range.to, "merchant", enabled);
  const topItems = useTopItems(range.from, range.to, orderBy, enabled);

  if (authLoading || !user) return <p className="text-slate-500">Loading…</p>;

  const setSearch = (patch: Partial<DashboardSearch>) =>
    void navigate({ to: "/dashboard", search: { ...search, ...patch } });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="font-serif font-semibold text-[30px] tracking-[-0.015em] text-slate-900">
          Dashboard
        </h1>
        <AddBillMenu />
      </div>

      {/* Desktop tab nav — mobile uses bottom nav bar in __root */}
      <div className="hidden sm:flex gap-6 border-b border-slate-200">
        {TABS.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setSearch({ tab: t })}
            className={
              "pb-3.5 text-[15px] font-medium capitalize relative transition-colors " +
              (tab === t
                ? "text-slate-900 after:absolute after:left-0 after:right-0 after:bottom-[-1px] after:h-[2.5px] after:bg-accent after:rounded-full"
                : "text-slate-400 hover:text-slate-700")
            }
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "splits" ? (
        <SplitsTab enabled={splitsEnabled} />
      ) : tab === "insights" ? (
        <CurrencyProvider>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <TimeRangePicker
              preset={preset}
              customFrom={search.from ?? ""}
              customTo={search.to ?? ""}
              onChange={(next) =>
                setSearch({
                  preset: next.preset,
                  from:
                    next.preset === "custom" ? next.customFrom || undefined : undefined,
                  to:
                    next.preset === "custom" ? next.customTo || undefined : undefined,
                })
              }
            />
            <CurrencyPicker />
          </div>
          <KpiCards
            data={overview.data}
            isLoading={overview.isLoading}
            isError={overview.isError}
          />
          <SpendOverTimeChart
            data={timeseries.data}
            granularity={granularity}
            isLoading={timeseries.isLoading}
            isError={timeseries.isError}
          />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <BreakdownChart
              title="By category"
              data={categoryBreakdown.data}
              isLoading={categoryBreakdown.isLoading}
              isError={categoryBreakdown.isError}
              barColor="#e0533d"
            />
            <BreakdownChart
              title="By merchant"
              data={merchantBreakdown.data}
              isLoading={merchantBreakdown.isLoading}
              isError={merchantBreakdown.isError}
              barColor="#1c1a17"
            />
          </div>
          <TopItemsTable
            data={topItems.data}
            isLoading={topItems.isLoading}
            isError={topItems.isError}
            orderBy={orderBy}
            onOrderByChange={(next) => setSearch({ order_by: next })}
            onSelect={setSelectedItem}
          />
          <ItemDetailDrawer
            normalizedName={selectedItem?.normalized_name ?? null}
            displayName={selectedItem?.name ?? ""}
            from={range.from}
            to={range.to}
            granularity={granularity}
            onClose={() => setSelectedItem(null)}
          />
        </CurrencyProvider>
      ) : (
        <BillsList />
      )}
    </div>
  );
}

export const Route = createFileRoute("/dashboard")({
  component: DashboardPage,
  validateSearch: (raw): DashboardSearch => {
    const r = raw as Record<string, unknown>;
    return {
      preset: isPreset(r.preset) ? r.preset : undefined,
      from: typeof r.from === "string" ? r.from : undefined,
      to: typeof r.to === "string" ? r.to : undefined,
      tab: isTab(r.tab) ? r.tab : undefined,
      order_by: isOrderBy(r.order_by) ? r.order_by : undefined,
    };
  },
});
