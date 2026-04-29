import { apiRequest, apiVoid } from "./fetcher";
import type {
  BillItemCreateRequest,
  BillItemUpdateRequest,
  BillListResponse,
  BillResponse,
  BillUpdateRequest,
  Dimension,
  Granularity,
  InsightsBreakdownResponse,
  InsightsOverviewResponse,
  InsightsTimeseriesResponse,
  InsightsTopItemsResponse,
  ItemOrderBy,
  LoginRequest,
  RegisterRequest,
  TokenResponse,
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
};
