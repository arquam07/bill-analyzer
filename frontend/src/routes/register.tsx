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
  const [language, setLanguage] = useState("en");
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
      await register(email, password, username, language, name || undefined);
      // navigation is handled by the useEffect above once user state updates
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Registration failed");
      setSubmitting(false);
    }
  }

  const inputCls = "mt-1 w-full border border-slate-300 rounded-xl px-3 py-3 text-base";

  return (
    <div className="min-h-[60vh] flex items-center justify-center py-8">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-md p-6 space-y-5">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Create account</h1>
          <p className="text-sm text-slate-500 mt-1">Start tracking your bills</p>
        </div>
        <form onSubmit={onSubmit} className="space-y-4">
          <label className="block text-sm">
            <span className="text-slate-700 font-medium">Email</span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={inputCls}
            />
          </label>
          <label className="block text-sm">
            <span className="text-slate-700 font-medium">Username</span>
            <input
              type="text"
              required
              minLength={3}
              maxLength={50}
              pattern="[a-z0-9]+"
              placeholder="lowercase letters and numbers"
              value={username}
              onChange={(e) => setUsername(e.target.value.toLowerCase().replace(/[^a-z0-9]/g, ""))}
              className={inputCls}
            />
          </label>
          <label className="block text-sm">
            <span className="text-slate-700 font-medium">Name (optional)</span>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className={inputCls}
            />
          </label>
          <label className="block text-sm">
            <span className="text-slate-700 font-medium">Password (min 8)</span>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={inputCls}
            />
          </label>
          <label className="block text-sm">
            <span className="text-slate-700 font-medium">Preferred language</span>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className={`${inputCls} bg-white`}
            >
              <option value="en">English</option>
              <option value="ja">日本語 (Japanese)</option>
            </select>
            <span className="block mt-1 text-xs text-slate-500">
              Bill extractions will be translated into this language.
            </span>
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
            {submitting ? "Creating…" : "Create account"}
          </button>
        </form>
        <p className="text-sm text-slate-600 text-center">
          Already have an account?{" "}
          <Link to="/login" className="text-slate-900 font-medium underline">
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
}

export const Route = createFileRoute("/register")({
  component: RegisterPage,
});
