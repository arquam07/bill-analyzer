import { useQuery } from "@tanstack/react-query";
import { insights as insightsApi } from "~/api/endpoints";
import type { Dimension, Granularity, ItemOrderBy } from "~/api/types";

export function useOverview(from: string, to: string, enabled = true) {
  return useQuery({
    queryKey: ["insights", "overview", from, to],
    queryFn: () => insightsApi.overview({ from, to }),
    enabled,
  });
}

export function useTimeseries(
  from: string,
  to: string,
  granularity: Granularity,
  enabled = true,
) {
  return useQuery({
    queryKey: ["insights", "timeseries", from, to, granularity],
    queryFn: () => insightsApi.timeseries({ from, to, granularity }),
    enabled,
  });
}

export function useBreakdown(
  from: string,
  to: string,
  dimension: Dimension,
  enabled = true,
) {
  return useQuery({
    queryKey: ["insights", "breakdown", from, to, dimension],
    queryFn: () => insightsApi.breakdown({ from, to, dimension, limit: 10 }),
    enabled,
  });
}

export function useTopItems(
  from: string,
  to: string,
  order_by: ItemOrderBy,
  enabled = true,
) {
  return useQuery({
    queryKey: ["insights", "items", from, to, order_by],
    queryFn: () => insightsApi.topItems({ from, to, order_by, limit: 20 }),
    enabled,
  });
}
