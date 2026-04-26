import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { bills as billsApi } from "~/api/endpoints";
import { ApiError } from "~/api/fetcher";
import { useAuth } from "~/auth/AuthContext";

function UploadPage() {
  const { user, isLoading: authLoading } = useAuth();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !user) void navigate({ to: "/login" });
  }, [authLoading, user, navigate]);

  useEffect(() => {
    if (!file) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const upload = useMutation({
    mutationFn: (f: File) => billsApi.upload(f),
    onSuccess: async (bill) => {
      await qc.invalidateQueries({ queryKey: ["bills"] });
      void navigate({ to: "/bills/$billId", params: { billId: bill.id } });
    },
  });

  if (authLoading || !user) return <p className="text-slate-500">Loading…</p>;

  return (
    <div className="max-w-md mx-auto bg-white border border-slate-200 rounded p-6 space-y-4">
      <h1 className="text-xl font-semibold">Upload a bill</h1>
      <input
        type="file"
        accept="image/jpeg,image/png"
        capture="environment"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        className="block w-full text-sm"
      />
      {previewUrl && (
        <img
          src={previewUrl}
          alt="preview"
          className="max-h-80 rounded border border-slate-200 mx-auto"
        />
      )}
      {upload.error && (
        <p className="text-sm text-red-600">
          {upload.error instanceof ApiError ? upload.error.detail : "Upload failed"}
        </p>
      )}
      <button
        type="button"
        disabled={!file || upload.isPending}
        onClick={() => file && upload.mutate(file)}
        className="w-full bg-slate-900 text-white rounded px-3 py-2 disabled:opacity-60"
      >
        {upload.isPending ? "Uploading…" : "Upload"}
      </button>
    </div>
  );
}

export const Route = createFileRoute("/upload")({
  component: UploadPage,
});
