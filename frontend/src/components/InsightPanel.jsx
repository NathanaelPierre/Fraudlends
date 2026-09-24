import { useState } from "react";
import { useTranslation } from "react-i18next";

const RISK_LEVEL_KEYS = [
  { key: "safe", tone: "safe" },
  { key: "suspicious", tone: "caution" },
  { key: "high_risk", tone: "risk" },
];

export default function InsightPanel({ collapsed, onToggle }) {
  const { t } = useTranslation();
  const [openKey, setOpenKey] = useState(null);

  return (
    <aside className={"insight-panel" + (collapsed ? " collapsed" : "")} aria-label="Awareness and risk guide">
      <button
        type="button"
        className="rail-collapse-btn rail-collapse-btn-left"
        onClick={onToggle}
        aria-label={collapsed ? "Expand panel" : "Collapse panel"}
        title={collapsed ? "Expand panel" : "Collapse panel"}
      >
        {collapsed ? "«" : "»"}
      </button>

      {!collapsed && (
        <div className="insight-panel-body">
          <div className="awareness-box">
            <div className="awareness-box-title">{t("insightPanel.stayAwareTitle")}</div>
            <p>{t("insightPanel.stayAwareBody")}</p>
          </div>

          <div className="risk-levels">
            <div className="risk-levels-title">{t("insightPanel.riskLevelsTitle")}</div>
            <ul className="risk-levels-list">
              {RISK_LEVEL_KEYS.map((level) => {
                const open = openKey === level.key;
                return (
                  <li key={level.key} className={"risk-level-item tone-" + level.tone}>
                    <button
                      type="button"
                      className="risk-level-toggle"
                      aria-expanded={open}
                      onClick={() => setOpenKey(open ? null : level.key)}
                    >
                      <span className={"risk-level-dot tone-" + level.tone} aria-hidden="true" />
                      <span className="risk-level-text">
                        <span className="risk-level-label">{t(`riskLevels.${level.key}.label`)}</span>
                        <span className="risk-level-summary">{t(`riskLevels.${level.key}.summary`)}</span>
                      </span>
                      <span className="risk-level-chevron">{open ? "–" : "+"}</span>
                    </button>
                    {open && <p className="risk-level-detail">{t(`riskLevels.${level.key}.detail`)}</p>}
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      )}
    </aside>
  );
}
