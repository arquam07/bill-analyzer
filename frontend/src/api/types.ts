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
  bills_missing_date: number;
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

export interface ItemTimeseriesPoint {
  period: string;
  total: number;
  count: number;
}

export interface ItemTimeseriesResponse {
  normalized_name: string;
  range_from: string;
  range_to: string;
  granularity: Granularity;
  total_spend: number;
  purchase_count: number;
  points: ItemTimeseriesPoint[];
}

// --- Split requests ---

export interface UserPublicResponse {
  id: string;
  username: string;
  name: string | null;
}

export interface SplitRequestBillSummary {
  merchant: string | null;
  total: number | null;
  billed_at: string | null;
}

export interface SplitRequestResponse {
  id: string;
  bill_id: string;
  from_username: string;
  to_username: string;
  amount: number;
  status: "pending" | "accepted" | "rejected";
  note: string | null;
  created_at: string;
  responded_at: string | null;
  bill: SplitRequestBillSummary;
}

export interface RecipientAssignment {
  username: string;
  bill_item_ids: string[];
}

export interface NonFriendInfo {
  username: string;
  amount: number;
  bill_item_ids: string[] | null;
}

export interface SplitRequestListResponse {
  items: SplitRequestResponse[];
  non_friends: NonFriendInfo[];
}

// --- Friends ---

export interface FriendResponse {
  user_id: string;
  username: string;
  name: string | null;
}

export interface FriendListResponse {
  friends: FriendResponse[];
}

export interface FriendRequestResponse {
  id: string;
  requester_username: string;
  addressee_username: string;
  status: "pending" | "accepted" | "rejected";
  created_at: string;
  responded_at: string | null;
}

export interface FriendRequestListResponse {
  items: FriendRequestResponse[];
}

export interface BalanceRow {
  username: string;
  user_id: string;
  net: number;
}

export interface BalancesResponse {
  balances: BalanceRow[];
}

export interface SettlementResponse {
  id: string;
  from_username: string;
  to_username: string;
  amount: number;
  note: string | null;
  created_at: string;
}
