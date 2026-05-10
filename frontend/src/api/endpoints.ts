import { apiRequest, apiVoid } from "./fetcher";
import type {
  BalancesResponse,
  BillItemCreateRequest,
  BillItemUpdateRequest,
  BillListResponse,
  BillResponse,
  BillUpdateRequest,
  Dimension,
  FriendListResponse,
  FriendRequestListResponse,
  FriendRequestResponse,
  Granularity,
  InsightsBreakdownResponse,
  InsightsOverviewResponse,
  InsightsTimeseriesResponse,
  InsightsTopItemsResponse,
  ItemOrderBy,
  ItemTimeseriesResponse,
  LoginRequest,
  RecipientAssignment,
  RegisterRequest,
  SettlementResponse,
  SplitRequestListResponse,
  SplitRequestResponse,
  TokenResponse,
  UserPublicResponse,
  UserResponse,
} from "./types";

export const auth = {
  register: (body: RegisterRequest) =>
    apiRequest<TokenResponse>("/auth/register", { method: "POST", body }),
  login: (body: LoginRequest) =>
    apiRequest<TokenResponse>("/auth/login", { method: "POST", body }),
  logout: () => apiVoid("/auth/logout", { method: "POST" }),
  me: () => apiRequest<UserResponse>("/me"),
};

export const bills = {
  list: (params: { limit?: number; offset?: number } = {}) => {
    const search = new URLSearchParams();
    if (params.limit !== undefined) search.set("limit", String(params.limit));
    if (params.offset !== undefined) search.set("offset", String(params.offset));
    const qs = search.toString();
    return apiRequest<BillListResponse>(`/bills${qs ? `?${qs}` : ""}`);
  },
  get: (id: string) => apiRequest<BillResponse>(`/bills/${id}`),
  upload: (file: File) => {
    const fd = new FormData();
    fd.append("image", file);
    return apiRequest<BillResponse>("/bills", { method: "POST", formData: fd });
  },
  createManual: (body: BillUpdateRequest = {}) =>
    apiRequest<BillResponse>("/bills/manual", { method: "POST", body }),
  patch: (id: string, body: BillUpdateRequest) =>
    apiRequest<BillResponse>(`/bills/${id}`, { method: "PATCH", body }),
  extract: (id: string) =>
    apiRequest<BillResponse>(`/bills/${id}/extract`, { method: "POST" }),
  finalize: (id: string) =>
    apiRequest<BillResponse>(`/bills/${id}/finalize`, { method: "POST" }),
  addItem: (id: string, body: BillItemCreateRequest) =>
    apiRequest<BillResponse>(`/bills/${id}/items`, { method: "POST", body }),
  updateItem: (id: string, itemId: string, body: BillItemUpdateRequest) =>
    apiRequest<BillResponse>(`/bills/${id}/items/${itemId}`, {
      method: "PATCH",
      body,
    }),
  deleteItem: (id: string, itemId: string) =>
    apiRequest<BillResponse>(`/bills/${id}/items/${itemId}`, { method: "DELETE" }),
  delete: (id: string) => apiVoid(`/bills/${id}`, { method: "DELETE" }),
};

export const splitRequests = {
  getUserByUsername: (username: string) =>
    apiRequest<UserPublicResponse>(`/users/by-username/${encodeURIComponent(username)}`),
  create: (
    billId: string,
    usernames: string[],
    options: { billItemIds?: string[]; totalToSplit?: number; assignments?: RecipientAssignment[]; ownerItemIds?: string[] } = {},
  ) =>
    apiRequest<SplitRequestListResponse>(`/bills/${billId}/split-requests`, {
      method: "POST",
      body: options.assignments
        ? { usernames: [], assignments: options.assignments, owner_item_ids: options.ownerItemIds }
        : { usernames, bill_item_ids: options.billItemIds, total_to_split: options.totalToSplit },
    }),
  listIncoming: () => apiRequest<SplitRequestListResponse>("/split-requests/incoming"),
  listOutgoing: () => apiRequest<SplitRequestListResponse>("/split-requests/outgoing"),
  accept: (id: string) =>
    apiRequest<SplitRequestResponse>(`/split-requests/${id}/accept`, { method: "POST" }),
  reject: (id: string) =>
    apiRequest<SplitRequestResponse>(`/split-requests/${id}/reject`, { method: "POST" }),
  balances: () => apiRequest<BalancesResponse>("/balances"),
  settle: (body: { username: string; amount: number; note?: string }) =>
    apiRequest<SettlementResponse>("/settlements", { method: "POST", body }),
};

export const friends = {
  list: () => apiRequest<FriendListResponse>("/friends"),
  sendRequest: (body: {
    username: string;
    deferred_split?: { bill_id: string; amount: number; bill_item_ids?: string[] };
  }) => apiRequest<FriendRequestResponse>("/friends/requests", { method: "POST", body }),
  listIncoming: () => apiRequest<FriendRequestListResponse>("/friends/requests/incoming"),
  listOutgoing: () => apiRequest<FriendRequestListResponse>("/friends/requests/outgoing"),
  accept: (id: string) =>
    apiRequest<FriendRequestResponse>(`/friends/requests/${id}/accept`, { method: "POST" }),
  reject: (id: string) =>
    apiRequest<FriendRequestResponse>(`/friends/requests/${id}/reject`, { method: "POST" }),
};

function rangeQs(params: { from: string; to: string }) {
  const s = new URLSearchParams();
  s.set("from", params.from);
  s.set("to", params.to);
  return s;
}

export const insights = {
  overview: (params: { from: string; to: string }) =>
    apiRequest<InsightsOverviewResponse>(`/insights/overview?${rangeQs(params)}`),
  timeseries: (params: { from: string; to: string; granularity: Granularity }) => {
    const s = rangeQs(params);
    s.set("granularity", params.granularity);
    return apiRequest<InsightsTimeseriesResponse>(`/insights/timeseries?${s}`);
  },
  breakdown: (params: {
    from: string;
    to: string;
    dimension: Dimension;
    limit?: number;
  }) => {
    const s = rangeQs(params);
    s.set("dimension", params.dimension);
    if (params.limit !== undefined) s.set("limit", String(params.limit));
    return apiRequest<InsightsBreakdownResponse>(`/insights/breakdown?${s}`);
  },
  topItems: (params: {
    from: string;
    to: string;
    order_by?: ItemOrderBy;
    limit?: number;
  }) => {
    const s = rangeQs(params);
    if (params.order_by) s.set("order_by", params.order_by);
    if (params.limit !== undefined) s.set("limit", String(params.limit));
    return apiRequest<InsightsTopItemsResponse>(`/insights/items?${s}`);
  },
  itemTimeseries: (params: {
    normalized_name: string;
    from: string;
    to: string;
    granularity: Granularity;
  }) => {
    const s = rangeQs(params);
    s.set("granularity", params.granularity);
    return apiRequest<ItemTimeseriesResponse>(
      `/insights/items/${encodeURIComponent(params.normalized_name)}/timeseries?${s}`,
    );
  },
};
