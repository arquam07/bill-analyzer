import { Link, Outlet, createRootRoute, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { useAuth } from "~/auth/AuthContext";

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
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-slate-200 bg-white">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/" className="font-semibold text-slate-900">
            Bill Analyzer
          </Link>
          <nav className="flex items-center gap-4 text-sm">
            {user ? (
              <>
                <Link to="/upload" className="text-slate-700 hover:text-slate-900">
                  Upload
                </Link>
                <span className="text-slate-500">{user.email}</span>
                <button
                  onClick={() => {
                    void logout().then(() => navigate({ to: "/login" }));
                  }}
                  className="text-slate-700 hover:text-slate-900"
                >
                  Log out
                </button>
              </>
            ) : isLoading ? (
              <span className="text-slate-400">…</span>
            ) : (
              <>
                <Link to="/login" className="text-slate-700">
                  Log in
                </Link>
                <Link to="/register" className="text-slate-700">
                  Register
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}

export const Route = createRootRoute({
  component: RootLayout,
});
