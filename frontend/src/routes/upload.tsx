import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { bills as billsApi } from "~/api/endpoints";
import { ApiError } from "~/api/fetcher";
import { useAuth } from "~/auth/AuthContext";

function CameraIcon() {
  return (
    <svg className="w-12 h-12 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.25}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.039l-.821 1.316z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0zM18.75 10.5h.008v.008h-.008V10.5z" />
    </svg>
  );
}

function UploadPage() {
  const { user, isLoading: authLoading } = useAuth();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

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
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["bills"] }),
        qc.invalidateQueries({ queryKey: ["insights"] }),
      ]);
      void navigate({ to: "/bills/$billId", params: { billId: bill.id } });
    },
  });

  if (authLoading || !user) return <p className="text-slate-500">Loading…</p>;

  return (
    <div className="max-w-md mx-auto space-y-4">
      <h1 className="text-2xl font-semibold text-slate-900">Upload a bill</h1>
      <p className="text-sm text-slate-500">Take a photo or choose an image from your library.</p>

      {/* Tap-to-select zone */}
      <label className="block cursor-pointer">
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png"
          capture="environment"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="sr-only"
        />
        <div
          className={`flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed p-10 transition-colors ${
            file
              ? "border-slate-400 bg-slate-50"
              : "border-slate-300 bg-white hover:border-slate-400 hover:bg-slate-50"
          }`}
        >
          {previewUrl ? (
            <img
              src={previewUrl}
              alt="preview"
              className="max-h-64 rounded-xl object-contain mx-auto"
            />
          ) : (
            <>
              <CameraIcon />
              <span className="text-sm font-medium text-slate-600">
                Tap to take a photo or choose an image
              </span>
              <span className="text-xs text-slate-400">JPEG or PNG · max 10 MB</span>
            </>
          )}
        </div>
      </label>

      {file && (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="w-full text-sm text-slate-500 hover:text-slate-800 py-1"
        >
          Change photo
        </button>
      )}

      {upload.error && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-xl px-4 py-3">
          {upload.error instanceof ApiError ? upload.error.detail : "Upload failed. Please try again."}
        </p>
      )}

      <button
        type="button"
        disabled={!file || upload.isPending}
        onClick={() => file && upload.mutate(file)}
        className="w-full bg-slate-900 text-white rounded-xl px-4 py-3.5 text-base font-medium disabled:opacity-50 hover:bg-slate-800 transition-colors"
      >
        {upload.isPending ? "Uploading…" : "Upload bill"}
      </button>
    </div>
  );
}

export const Route = createFileRoute("/upload")({
  component: UploadPage,
});
