import type { components } from "./types.gen";

type Schemas = components["schemas"];

export type UserResponse = Schemas["UserResponse"];
export type TokenResponse = Schemas["TokenResponse"];
export type RegisterRequest = Schemas["RegisterRequest"];
export type LoginRequest = Schemas["LoginRequest"];

export type BillResponse = Schemas["BillResponse"];
export type BillSummaryResponse = Schemas["BillSummaryResponse"];
export type BillItemResponse = Schemas["BillItemResponse"];
export type BillListResponse = Schemas["BillListResponse"];
export type BillUpdateRequest = Schemas["BillUpdateRequest"];
export type BillItemCreateRequest = Schemas["BillItemCreateRequest"];
export type BillItemUpdateRequest = Schemas["BillItemUpdateRequest"];

export type BillStatus = "uploaded" | "extracted" | "reviewed";

// --- Insights ---
// Hand-mirrored from backend until `npm run gen-types` regenerates types.gen.ts.
export type Granularity = "day" | "week" | "month";

export interface InsightsOverviewResponse {
  range_from: string;
  range_to: string;
  total_spend: number;
  bill_count: number;
  avg_bill: number;
  top_category: string | null;
  top_merchant: string | null;
  prev_total_spend: number;
  spend_delta_pct: number | null;
}

export interface TimeseriesPoint {
  period: string;
  total: number;
  count: number;
}

export interface InsightsTimeseriesResponse {
  range_from: string;
  range_to: string;
  granularity: Granularity;
  points: TimeseriesPoint[];
}

export type Dimension = "category" | "merchant";
export type ItemOrderBy = "spend" | "frequency";

export interface BreakdownRow {
  label: string;
  total: number;
  count: number;
}

export interface InsightsBreakdownResponse {
  range_from: string;
  range_to: string;
  dimension: Dimension;
  rows: BreakdownRow[];
}

export interface TopItem {
  name: string;
  normalized_name: string;
  total_spend: number;
  purchase_count: number;
  last_purchased: string | null;
}

export interface InsightsTopItemsResponse {
  range_from: string;
  range_to: string;
  order_by: ItemOrderBy;
  rows: TopItem[];
}
