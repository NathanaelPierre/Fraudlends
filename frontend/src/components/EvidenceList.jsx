import { useTranslation } from "react-i18next";

const SEVERITY_KEY = {
  info: "severityInfo",
  suspicious: "severitySuspicious",
  high_risk: "severityHighRisk",
};

const CATEGORY_KEY = {
  registry: "categoryRegistry",
  indicator: "categoryIndicator",
  domain: "categoryDomain",
  phone: "categoryPhone",
};

// Renders the structured evidence trail the backend already computes
// (schemas.EvidenceItem list) - one line per signal source that
// contributed to the verdict. Note: the item descriptions themselves
// (item.description) are already translated server-side, in whatever
// language the checked message was detected as (see
// app/explanations_i18n.py) — only the category and severity labels
// wrapped around them are translated here, using the UI's own current
// language, since those are this frontend's own labels, not part of
// the message-language-dependent analysis itself.
export default function EvidenceList({ evidence }) {
  const { t } = useTranslation();

  if (!Array.isArray(evidence) || evidence.length === 0) return null;

  return (
    <div className="evidence-list">
      <h4 className="evidence-list-title">{t("evidence.title")}</h4>
      <ul>
        {evidence.map((item, i) => (
          <li key={i} className={`evidence-item severity-${item.severity}`}>
            <span className="evidence-category">
              {t(`evidence.${CATEGORY_KEY[item.category] || item.category}`, item.category)}
            </span>
            <span className="evidence-description">{item.description}</span>
            <span className={`evidence-severity-tag severity-${item.severity}`}>
              {t(`evidence.${SEVERITY_KEY[item.severity] || item.severity}`, item.severity)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
