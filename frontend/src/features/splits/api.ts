import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { friends as friendsApi, splitRequests as api } from "~/api/endpoints";

export function useIncomingRequests(enabled = true) {
  return useQuery({
    queryKey: ["split-requests", "incoming"],
    queryFn: () => api.listIncoming(),
    enabled,
  });
}

export function useOutgoingRequests(enabled = true) {
  return useQuery({
    queryKey: ["split-requests", "outgoing"],
    queryFn: () => api.listOutgoing(),
    enabled,
  });
}

export function useBalances(enabled = true) {
  return useQuery({
    queryKey: ["balances"],
    queryFn: () => api.balances(),
    enabled,
  });
}

export function useAcceptRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.accept(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["split-requests"] });
      void qc.invalidateQueries({ queryKey: ["balances"] });
    },
  });
}

export function useRejectRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.reject(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["split-requests"] });
    },
  });
}

export function useSettle() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      username: string;
      amount: number;
      direction: "paid" | "received";
      note?: string;
    }) => api.settle(body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["settlements"] });
    },
  });
}

export function useIncomingSettlements(enabled = true) {
  return useQuery({
    queryKey: ["settlements", "incoming"],
    queryFn: () => api.listIncomingSettlements(),
    enabled,
  });
}

export function useOutgoingSettlements(enabled = true) {
  return useQuery({
    queryKey: ["settlements", "outgoing"],
    queryFn: () => api.listOutgoingSettlements(),
    enabled,
  });
}

export function useAcceptSettlement() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.acceptSettlement(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["settlements"] });
      void qc.invalidateQueries({ queryKey: ["balances"] });
    },
  });
}

export function useRejectSettlement() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.rejectSettlement(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["settlements"] });
    },
  });
}

export function useFriends(enabled = true) {
  return useQuery({
    queryKey: ["friends"],
    queryFn: () => friendsApi.list(),
    enabled,
  });
}

export function useIncomingFriendRequests(enabled = true) {
  return useQuery({
    queryKey: ["friend-requests", "incoming"],
    queryFn: () => friendsApi.listIncoming(),
    enabled,
  });
}

export function useAcceptFriendRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => friendsApi.accept(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["friend-requests"] });
      void qc.invalidateQueries({ queryKey: ["friends"] });
      void qc.invalidateQueries({ queryKey: ["split-requests"] });
    },
  });
}

export function useRejectFriendRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => friendsApi.reject(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["friend-requests"] });
    },
  });
}

export function useSendFriendRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      username: string;
      deferred_split?: { bill_id: string; amount: number; bill_item_ids?: string[] };
    }) => friendsApi.sendRequest(body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["friend-requests"] });
    },
  });
}
