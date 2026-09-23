import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import FolderNav from "./FolderNav";
import InsightPanel from "./InsightPanel";

const NAV_KEY = "klaro_nav_collapsed";
const PANEL_KEY = "klaro_panel_collapsed";

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  const [navCollapsed, setNavCollapsed] = useState(() => localStorage.getItem(NAV_KEY) === "1");
  const [panelCollapsed, setPanelCollapsed] = useState(() => localStorage.getItem(PANEL_KEY) === "1");

  useEffect(() => {
    localStorage.setItem(NAV_KEY, navCollapsed ? "1" : "0");
  }, [navCollapsed]);

  useEffect(() => {
    localStorage.setItem(PANEL_KEY, panelCollapsed ? "1" : "0");
  }, [panelCollapsed]);

  if (loading) {
    return <div className="loading-screen">Loading your account…</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="app-shell">
      <FolderNav collapsed={navCollapsed} onToggle={() => setNavCollapsed((v) => !v)} />
      <main className="app-main">{children}</main>
      <InsightPanel collapsed={panelCollapsed} onToggle={() => setPanelCollapsed((v) => !v)} />
    </div>
  );
}
