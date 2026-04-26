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
