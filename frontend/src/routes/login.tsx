import { Link, createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useAuth } from "~/auth/AuthContext";
import { ApiError } from "~/api/fetcher";

function LoginPage() {
  const { user, isLoading, login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!isLoading && user) void navigate({ to: "/dashboard" });
  }, [user, isLoading, navigate]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      // navigation is handled by the useEffect above once user state updates
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Login failed");
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-[60vh] flex items-center justify-center py-8">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-md p-6 space-y-5">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Welcome back</h1>
          <p className="text-sm text-slate-500 mt-1">Log in to your account</p>
        </div>
        <form onSubmit={onSubmit} className="space-y-4">
          <label className="block text-sm">
            <span className="text-slate-700 font-medium">Email</span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full border border-slate-300 rounded-xl px-3 py-3 text-base"
            />
          </label>
          <label className="block text-sm">
            <span className="text-slate-700 font-medium">Password</span>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full border border-slate-300 rounded-xl px-3 py-3 text-base"
            />
          </label>
          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-xl px-3 py-2">
              {error}
            </p>
          )}
          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-slate-900 text-white rounded-xl px-3 py-3 text-base font-medium disabled:opacity-60 hover:bg-slate-800 transition-colors"
          >
            {submitting ? "Logging in…" : "Log in"}
          </button>
        </form>
        <p className="text-sm text-slate-600 text-center">
          New here?{" "}
          <Link to="/register" className="text-slate-900 font-medium underline">
            Create an account
          </Link>
        </p>
      </div>
    </div>
  );
}

export const Route = createFileRoute("/login")({
  component: LoginPage,
});
