import { apiRequest, apiVoid } from "./fetcher";
import type {
  BillItemCreateRequest,
  BillItemUpdateRequest,
  BillListResponse,
  BillResponse,
  BillUpdateRequest,
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
