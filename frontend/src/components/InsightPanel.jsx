import { useState } from "react";

const RISK_LEVELS = [
  {
    key: "safe",
    tone: "safe",
    label: "Verified",
    summary: "Matches a real institution",
    detail:
      "The claimed sender's name matches an entity in the Bank of Mauritius registry snapshot. This confirms the name is genuinely registered — it does not confirm this specific message was sent by them. Always reach the institution through its own official channels before acting.",
  },
  {
    key: "suspicious",
    tone: "caution",
    label: "Unverified",
    summary: "Not found, or only a close match",
    detail:
      "No exact match was found in the registry, or the name is only a close (not exact) match to a registered entity. This isn't proof of fraud — many legitimate senders simply sit outside this registry — but it means the name couldn't be confirmed, so treat it with extra caution.",
  },
  {
    key: "high_risk",
    tone: "risk",
    label: "High risk",
    summary: "Name mismatch / possible impersonation",
    detail:
      "The claimed sender's name resembles a registered institution closely enough to suggest deliberate impersonation, without being an exact match. This is the strongest warning sign Klaro can surface — avoid clicking links, sharing OTPs, or sending money until you've verified through the institution's own official channels.",
  },
];

export default function InsightPanel({ collapsed, onToggle }) {
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
            <div className="awareness-box-title">Stay aware</div>
            <p>
              Genuine banks never ask you to share an OTP, PIN, or full card number over SMS, email, or
              WhatsApp. If a message pressures you to act immediately, that urgency is itself a warning
              sign — slow down and verify independently.
            </p>
          </div>

          <div className="risk-levels">
            <div className="risk-levels-title">Risk levels</div>
            <ul className="risk-levels-list">
              {RISK_LEVELS.map((level) => {
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
                        <span className="risk-level-label">{level.label}</span>
                        <span className="risk-level-summary">{level.summary}</span>
                      </span>
                      <span className="risk-level-chevron">{open ? "–" : "+"}</span>
                    </button>
                    {open && <p className="risk-level-detail">{level.detail}</p>}
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
