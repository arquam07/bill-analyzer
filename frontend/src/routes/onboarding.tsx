import { createFileRoute, useLocation, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { auth as authApi } from "~/api/endpoints";
import { ApiError } from "~/api/fetcher";
import type { GooglePendingState } from "~/auth/AuthContext";
import { useAuth } from "~/auth/AuthContext";

const USERNAME_RE = /^[a-z0-9]{3,50}$/;

function OnboardingPage() {
  const navigate = useNavigate();
  const { completeOnboarding } = useAuth();
  const location = useLocation();
  const pending = (location.state as unknown as GooglePendingState | null | undefined) ?? null;

  const [username, setUsername] = useState("");
  const [language, setLanguage] = useState("en");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // If someone navigates here directly with no state, bounce to register
  useEffect(() => {
    if (!pending?.idToken) void navigate({ to: "/register" });
  }, [pending, navigate]);

  if (!pending?.idToken) return null;

  const usernameValid = USERNAME_RE.test(username);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!usernameValid) {
      setError("Username must be 3–50 lowercase letters and numbers only");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const res = await authApi.googleComplete({
        id_token: pending!.idToken,
        username,
        preferred_language: language,
      });
      await completeOnboarding(res.user, res.token);
      void navigate({ to: "/dashboard" });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Something went wrong. Please try again.");
      setSubmitting(false);
    }
  }

  const inputCls = "mt-1 w-full border border-slate-300 rounded-xl px-3 py-3 text-base focus:outline-none focus:ring-2 focus:ring-slate-400";

  return (
    <div className="min-h-[60vh] flex items-center justify-center py-8">
      <div className="w-full max-w-sm bg-card rounded-2xl shadow-md p-6 space-y-5">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            {pending.name ? `Welcome, ${pending.name.split(" ")[0]}!` : "Almost there!"}
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Just two quick things before you start.
          </p>
        </div>

        <form onSubmit={onSubmit} className="space-y-5">
          <div>
            <label className="block text-sm">
              <span className="text-slate-700 font-medium">Choose a username</span>
              <div className="relative">
                <input
                  type="text"
                  required
                  minLength={3}
                  maxLength={50}
                  placeholder="lowercase letters and numbers"
                  value={username}
                  onChange={(e) =>
                    setUsername(e.target.value.toLowerCase().replace(/[^a-z0-9]/g, ""))
                  }
                  className={`${inputCls} pr-8`}
                />
                {username.length >= 3 && (
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm">
                    {usernameValid ? "✓" : "✗"}
                  </span>
                )}
              </div>
            </label>
            <p className="mt-1 text-xs text-slate-500">
              Friends use this to find you when splitting bills.
            </p>
          </div>

          <div>
            <span className="block text-sm font-medium text-slate-700 mb-2">
              Preferred language for receipts
            </span>
            <div className="space-y-2">
              {[
                { value: "en", label: "English" },
                { value: "ja", label: "日本語 (Japanese)" },
              ].map(({ value, label }) => (
                <label
                  key={value}
                  className={`flex items-center gap-3 border rounded-xl px-4 py-3 cursor-pointer transition-colors ${
                    language === value
                      ? "border-slate-900 bg-slate-50"
                      : "border-slate-200 hover:border-slate-300"
                  }`}
                >
                  <input
                    type="radio"
                    name="language"
                    value={value}
                    checked={language === value}
                    onChange={() => setLanguage(value)}
                    className="accent-slate-900"
                  />
                  <span className="text-sm font-medium text-slate-800">{label}</span>
                </label>
              ))}
            </div>
            <p className="mt-1.5 text-xs text-slate-500">
              Bill extractions will be translated into this language.
            </p>
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-xl px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={submitting || !usernameValid}
            className="w-full bg-accent text-white rounded-xl px-3 py-3 text-base font-semibold disabled:opacity-60 hover:bg-accent-deep transition-colors"
          >
            {submitting ? "Setting up…" : "Get started →"}
          </button>
        </form>
      </div>
    </div>
  );
}

export const Route = createFileRoute("/onboarding")({
  component: OnboardingPage,
});
