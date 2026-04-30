import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { splitRequests as api } from "~/api/endpoints";

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
    mutationFn: (body: { username: string; amount: number; note?: string }) =>
      api.settle(body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["balances"] });
    },
  });
}
