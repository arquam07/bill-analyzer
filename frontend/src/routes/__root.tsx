import { Link, Outlet, createRootRoute, useNavigate, useRouterState } from "@tanstack/react-router";
import { useEffect } from "react";
import { useAuth } from "~/auth/AuthContext";

type BottomTab = "insights" | "history" | "splits";

const BOTTOM_NAV: { key: BottomTab; label: string }[] = [
  { key: "insights", label: "Insights" },
  { key: "history", label: "Bills" },
  { key: "splits", label: "Splits" },
];

function HomeIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" className="w-6 h-6">
      <path d="M3 12l9-9 9 9v9a1 1 0 01-1 1H4a1 1 0 01-1-1z" />
      <path d="M9 22V12h6v10" />
    </svg>
  );
}

function ListIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" className="w-6 h-6">
      <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2" />
      <rect x="9" y="3" width="6" height="4" rx="1" />
      <line x1="9" y1="12" x2="15" y2="12" />
      <line x1="9" y1="16" x2="13" y2="16" />
    </svg>
  );
}

function SplitIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" className="w-6 h-6">
      <polyline points="17 1 21 5 17 9" />
      <path d="M3 11V9a4 4 0 014-4h14" />
      <polyline points="7 23 3 19 7 15" />
      <path d="M21 13v2a4 4 0 01-4 4H3" />
    </svg>
  );
}

const TAB_ICONS: Record<BottomTab, () => JSX.Element> = {
  insights: HomeIcon,
  history: ListIcon,
  splits: SplitIcon,
};

function BottomNav() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const routerState = useRouterState();

  if (!user) return null;

  const params = new URLSearchParams(routerState.location.search);
  const activeTab = params.get("tab") ?? "insights";
  const activePath = routerState.location.pathname;

  function isActive(key: string) {
    return activePath === "/dashboard" && activeTab === key;
  }

  return (
    <nav className="fixed bottom-0 left-0 right-0 sm:hidden bg-white border-t border-slate-200 z-40">
      <div className="flex">
        {BOTTOM_NAV.map(({ key, label }) => {
          const active = isActive(key);
          const Icon = TAB_ICONS[key];
          return (
            <button
              key={key}
              type="button"
              onClick={() =>
                void navigate({
                  to: "/dashboard",
                  search: { tab: key as BottomTab },
                })
              }
              className={`flex-1 flex flex-col items-center justify-center gap-0.5 py-2 min-h-[56px] text-xs font-medium transition-colors ${
                active ? "text-slate-900" : "text-slate-400"
              }`}
            >
              <Icon />
              {label}
            </button>
          );
        })}
      </div>
    </nav>
  );
}

function RootLayout() {
  const { user, isLoading, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const onUnauth = () => {
      void navigate({ to: "/login" });
    };
    window.addEventListener("auth:unauthorized", onUnauth);
    return () => window.removeEventListener("auth:unauthorized", onUnauth);
  }, [navigate]);

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/" className="font-bold text-slate-900 text-lg tracking-tight">
            Bill Analyzer
          </Link>
          <nav className="flex items-center gap-3 text-sm">
            {user ? (
              <>
                <Link to="/dashboard" className="hidden sm:block text-slate-600 hover:text-slate-900">
                  Dashboard
                </Link>
                <Link to="/upload" className="hidden sm:block text-slate-600 hover:text-slate-900">
                  Upload
                </Link>
                <span className="text-slate-500 text-sm hidden sm:inline">@{user.username}</span>
                <span className="text-slate-500 text-sm sm:hidden">@{user.username.slice(0, 8)}</span>
                <button
                  onClick={() => {
                    void logout().then(() => navigate({ to: "/login" }));
                  }}
                  className="text-slate-500 hover:text-slate-900 text-sm"
                >
                  Log out
                </button>
              </>
            ) : isLoading ? (
              <span className="text-slate-400">…</span>
            ) : (
              <>
                <Link to="/login" className="text-slate-700 hover:text-slate-900">
                  Log in
                </Link>
                <Link
                  to="/register"
                  className="bg-slate-900 text-white text-sm rounded-lg px-4 py-2 hover:bg-slate-800"
                >
                  Sign up
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className={`flex-1 max-w-4xl w-full mx-auto px-4 py-6 ${user ? "pb-20 sm:pb-6" : ""}`}>
        <Outlet />
      </main>
      <BottomNav />
    </div>
  );
}

export const Route = createRootRoute({
  component: RootLayout,
});
