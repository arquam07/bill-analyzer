import { Link, createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useAuth } from "~/auth/AuthContext";
import { ApiError } from "~/api/fetcher";

function RegisterPage() {
  const { user, isLoading, register } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!isLoading && user) void navigate({ to: "/dashboard" });
  }, [user, isLoading, navigate]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!/^[a-z0-9]{3,50}$/.test(username)) {
      setError("Username must be 3–50 lowercase letters and numbers only");
      return;
    }
    setSubmitting(true);
    try {
      await register(email, password, username, name || undefined);
      // navigation is handled by the useEffect above once user state updates
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Registration failed");
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-sm mx-auto bg-white border border-slate-200 rounded p-6 space-y-4">
      <h1 className="text-xl font-semibold">Create account</h1>
      <form onSubmit={onSubmit} className="space-y-3">
        <label className="block text-sm">
          <span className="text-slate-700">Email</span>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full border border-slate-300 rounded px-3 py-2"
          />
        </label>
        <label className="block text-sm">
          <span className="text-slate-700">Username</span>
          <input
            type="text"
            required
            minLength={3}
            maxLength={50}
            pattern="[a-z0-9]+"
            placeholder="lowercase letters and numbers"
            value={username}
            onChange={(e) => setUsername(e.target.value.toLowerCase().replace(/[^a-z0-9]/g, ""))}
            className="mt-1 w-full border border-slate-300 rounded px-3 py-2"
          />
        </label>
        <label className="block text-sm">
          <span className="text-slate-700">Name (optional)</span>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 w-full border border-slate-300 rounded px-3 py-2"
          />
        </label>
        <label className="block text-sm">
          <span className="text-slate-700">Password (min 8)</span>
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 w-full border border-slate-300 rounded px-3 py-2"
          />
        </label>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="w-full bg-slate-900 text-white rounded px-3 py-2 disabled:opacity-60"
        >
          {submitting ? "Creating…" : "Create account"}
        </button>
      </form>
      <p className="text-sm text-slate-600">
        Already have an account?{" "}
        <Link to="/login" className="text-slate-900 underline">
          Log in
        </Link>
      </p>
    </div>
  );
}

export const Route = createFileRoute("/register")({
  component: RegisterPage,
});
