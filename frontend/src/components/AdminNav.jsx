import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const TABS = [
  { to: "/admin", label: "Overview", end: true, icon: "pulse" },
  { to: "/admin/checks", label: "Checks", icon: "search" },
  { to: "/admin/security", label: "Security", icon: "shield" },
  { to: "/admin/users", label: "Users", icon: "users" },
];

const ICONS = {
  pulse: <path d="M3 12h4l2-7 4 14 2-7h6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />,
  search: <path d="M10 4a6 6 0 1 0 3.8 10.7l4.5 4.5 1.4-1.4-4.5-4.5A6 6 0 0 0 10 4Zm0 2a4 4 0 1 1 0 8 4 4 0 0 1 0-8Z" />,
  shield: <path d="M11 2 3 5v6c0 5 3.4 8.6 8 9 4.6-.4 8-4 8-9V5l-8-3Zm0 2.2 6 2.2v4.6c0 4-2.6 6.7-6 7.1-3.4-.4-6-3.1-6-7.1V6.4l6-2.2Zm-1.2 9.5-2.6-2.6 1.4-1.4 1.2 1.2 3.6-3.6 1.4 1.4-5 5Z" />,
  users: <path d="M8 12a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm8 0a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM2 19c0-2.8 2.7-4.5 6-4.5s6 1.7 6 4.5v1H2v-1Zm12.2-4.4c2.7.4 5.8 1.9 5.8 4.4v1h-4v-1c0-1.6-.7-3-1.8-4.4Z" />,
};

function Icon({ name }) {
  return (
    <svg className="folder-tab-icon" viewBox="0 0 22 22" width="18" height="18" aria-hidden="true">
      {ICONS[name]}
    </svg>
  );
}

export default function AdminNav({ collapsed, onToggle }) {
  const { user, logout } = useAuth();

  return (
    <nav className={"folder-nav admin-nav" + (collapsed ? " collapsed" : "")} aria-label="Admin">
      <div className="folder-nav-mark">
        <span className="admin-nav-dot" aria-hidden="true" />
        {!collapsed && (
          <div>
            <div className="folder-nav-title">Ops console</div>
            <div className="folder-nav-sub">FraudLens admin</div>
          </div>
        )}
      </div>

      <ul className="folder-nav-tabs">
        {TABS.map((tab) => (
          <li key={tab.to}>
            <NavLink
              to={tab.to}
              end={tab.end}
              className={({ isActive }) => "folder-tab" + (isActive ? " active" : "")}
              title={collapsed ? tab.label : undefined}
            >
              <Icon name={tab.icon} />
              {!collapsed && <span>{tab.label}</span>}
            </NavLink>
          </li>
        ))}
      </ul>

      <div className="folder-nav-footer">
        {!collapsed && (
          <NavLink to="/app" className="admin-nav-back">
            ← Back to app
          </NavLink>
        )}
        {!collapsed && user && (
          <div className="folder-nav-user" title={user.email}>
            {user.email}
          </div>
        )}
        <div className="folder-nav-footer-row">
          <button
            className={"btn btn-ghost" + (collapsed ? "" : " btn-block")}
            onClick={logout}
            type="button"
            title={collapsed ? "Log out" : undefined}
          >
            {collapsed ? "⎋" : "Log out"}
          </button>
        </div>
      </div>

      <button
        type="button"
        className="rail-collapse-btn"
        onClick={onToggle}
        aria-label={collapsed ? "Expand navigation" : "Collapse navigation"}
        title={collapsed ? "Expand navigation" : "Collapse navigation"}
      >
        {collapsed ? "»" : "«"}
      </button>
    </nav>
  );
}
