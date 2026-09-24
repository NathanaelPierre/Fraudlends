import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../context/AuthContext";
import LanguageSwitcher from "./LanguageSwitcher";

const TABS = [
  { to: "/app", labelKey: "nav.home", end: true, icon: "home" },
  { to: "/community", labelKey: "nav.community", icon: "community" },
  { to: "/history", labelKey: "nav.history", icon: "history" },
  { to: "/insights", labelKey: "nav.insights", icon: "insights" },
  { to: "/settings", labelKey: "nav.settings", icon: "settings" },
];

const ICONS = {
  home: (
    <path d="M4 10.5 12 4l8 6.5V19a1 1 0 0 1-1 1h-4.5v-6h-5v6H5a1 1 0 0 1-1-1z" />
  ),
  community: (
    <path d="M8 12a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm8 0a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM2 19c0-2.8 2.7-4.5 6-4.5s6 1.7 6 4.5v1H2v-1Zm12.2-4.4c2.7.4 5.8 1.9 5.8 4.4v1h-4v-1c0-1.6-.7-3-1.8-4.4Z" />
  ),
  history: (
    <path d="M12 4a8 8 0 1 1-7.6 5.5 1 1 0 0 1 1.9.6A6 6 0 1 0 12 6a5.9 5.9 0 0 0-4.2 1.8H10v2H4V4h2v2.5A8 8 0 0 1 12 4Zm-1 4h1.5v4.2l3.3 2-1 1.5-3.8-2.3Z" />
  ),
  settings: (
    <path d="m19.4 13-1.6-1a6.9 6.9 0 0 0 0-2l1.6-1a1 1 0 0 0 .4-1.3l-1.6-2.8a1 1 0 0 0-1.2-.5l-1.8.7a7 7 0 0 0-1.7-1L13.2 2a1 1 0 0 0-1-.8h-3.4a1 1 0 0 0-1 .8l-.3 1.9a7 7 0 0 0-1.7 1l-1.8-.7a1 1 0 0 0-1.2.5L1.4 7.5a1 1 0 0 0 .4 1.3l1.6 1a6.9 6.9 0 0 0 0 2l-1.6 1a1 1 0 0 0-.4 1.3l1.7 2.8a1 1 0 0 0 1.2.5l1.8-.7a7 7 0 0 0 1.7 1l.3 1.9a1 1 0 0 0 1 .8h3.4a1 1 0 0 0 1-.8l.3-1.9a7 7 0 0 0 1.7-1l1.8.7a1 1 0 0 0 1.2-.5l1.6-2.8a1 1 0 0 0-.4-1.3ZM10.5 15a3 3 0 1 1 0-6 3 3 0 0 1 0 6Z" />
  ),
  insights: (
    <path d="M4 20V10h3v10H4Zm6.5 0V4h3v16h-3ZM17 20v-7h3v7h-3Z" />
  ),
};

function Icon({ name }) {
  return (
    <svg className="folder-tab-icon" viewBox="0 0 22 22" width="18" height="18" aria-hidden="true">
      {ICONS[name]}
    </svg>
  );
}

export default function FolderNav({ collapsed, onToggle }) {
  const { user, logout } = useAuth();
  const { t } = useTranslation();
  const mark = "/cipher-mark-blue.png";

  return (
    <nav className={"folder-nav" + (collapsed ? " collapsed" : "")} aria-label="Primary">
      <div className="folder-nav-mark">
        <img src={mark} alt="Klaro" className="folder-nav-mark-glyph" />
        {!collapsed && (
          <div>
            <div className="folder-nav-title">Klaro</div>
            <div className="folder-nav-sub">{t("nav.subtitle")}</div>
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
              title={collapsed ? t(tab.labelKey) : undefined}
            >
              <Icon name={tab.icon} />
              {!collapsed && <span>{t(tab.labelKey)}</span>}
            </NavLink>
          </li>
        ))}
      </ul>

      <div className="folder-nav-footer">
        {!collapsed && user?.role === "admin" && (
          <NavLink to="/admin" className="admin-nav-back admin-console-link">
            {t("nav.adminConsole")}
          </NavLink>
        )}
        {!collapsed && user && (
          <div className="folder-nav-user" title={user.email}>
            {user.email}
          </div>
        )}
        <LanguageSwitcher collapsed={collapsed} />
        <div className="folder-nav-footer-row">
          <button
            className={"btn btn-ghost" + (collapsed ? "" : " btn-block")}
            onClick={logout}
            type="button"
            title={collapsed ? t("nav.logout") : undefined}
          >
            {collapsed ? "⎋" : t("nav.logout")}
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
