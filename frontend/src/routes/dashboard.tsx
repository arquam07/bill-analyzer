import { Link, createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
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
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <Link
          to="/upload"
          className="bg-slate-900 text-white text-sm rounded px-3 py-2 hover:bg-slate-800"
        >
          Upload bill
        </Link>
      </div>

      <div className="border-b border-slate-200">
        <nav className="-mb-px flex gap-4 text-sm">
          {TABS.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setSearch({ tab: t })}
              className={
                "px-1 pb-2 border-b-2 capitalize " +
                (tab === t
                  ? "border-slate-900 text-slate-900 font-medium"
                  : "border-transparent text-slate-500 hover:text-slate-700")
              }
            >
              {t}
            </button>
          ))}
        </nav>
      </div>

      {tab === "splits" ? (
        <SplitsTab enabled={splitsEnabled} />
      ) : tab === "insights" ? (
        <>
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
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            <BreakdownChart
              title="By category"
              data={categoryBreakdown.data}
              isLoading={categoryBreakdown.isLoading}
              isError={categoryBreakdown.isError}
            />
            <BreakdownChart
              title="By merchant"
              data={merchantBreakdown.data}
              isLoading={merchantBreakdown.isLoading}
              isError={merchantBreakdown.isError}
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
        </>
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
