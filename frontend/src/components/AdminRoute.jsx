import { useEffect, useState } from "react";
import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import AdminNav from "./AdminNav";

const NAV_KEY = "klaro_admin_nav_collapsed";

export default function AdminRoute() {
  const { user, loading } = useAuth();
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(NAV_KEY) === "1");

  useEffect(() => {
    localStorage.setItem(NAV_KEY, collapsed ? "1" : "0");
  }, [collapsed]);

  if (loading) {
    return <div className="loading-screen">Loading your account…</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // Deliberately no distinct "not authorized" screen for a
  // non-admin — a role check that reveals its own existence is a
  // minor information leak for no real benefit here. Non-admins are
  // routed straight back to the app they do have access to.
  if (user.role !== "admin") {
    return <Navigate to="/app" replace />;
  }

  return (
    <div className="app-shell admin-shell">
      <AdminNav collapsed={collapsed} onToggle={() => setCollapsed((v) => !v)} />
      <main className="app-main admin-main">
        <Outlet />
      </main>
    </div>
  );
}
