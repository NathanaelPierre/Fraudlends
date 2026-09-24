import { useTranslation } from "react-i18next";

const STATUS_KEY = {
  verified: "statusVerified",
  not_found: "statusNotFound",
  revoked: "statusRevoked",
  name_mismatch: "statusNameMismatch",
  no_sender_given: "statusNoSender",
  registry_unavailable: "statusUnavailable",
};

const SIGNAL_KEY = {
  registry_only: "signalRegistryOnly",
  registry_and_indicators: "signalRegistryIndicators",
  ai: "signalAi",
};

export default function RegistryRecord({ check }) {
  const { t } = useTranslation();

  const statusLabel = STATUS_KEY[check.registry_match_status]
    ? t(`registryRecord.${STATUS_KEY[check.registry_match_status]}`)
    : check.registry_match_status;

  const signalLabel = SIGNAL_KEY[check.explanation_source]
    ? t(`registryRecord.${SIGNAL_KEY[check.explanation_source]}`)
    : check.explanation_source || t("registryRecord.signalRegistryOnly");

  const senderValue = check.claimed_sender ? (
    <>
      {check.claimed_sender}
      {check.sender_auto_detected && (
        <span
          className="detected-tag"
          title={`${t("registryRecord.detected")}: "${check.sender_detection_source_text}"`}
        >
          {" "}{t("registryRecord.detected")}
        </span>
      )}
    </>
  ) : (
    "—"
  );

  const rows = [
    [t("registryRecord.claimedSender"), senderValue],
    [t("registryRecord.registryStatus"), statusLabel],
  ];

  if (check.registry_matched_entity) {
    rows.push([t("registryRecord.closestEntity"), check.registry_matched_entity]);
  }
  if (check.registry_status_detail) {
    rows.push([t("registryRecord.licenseStatus"), check.registry_status_detail]);
  }
  if (typeof check.registry_match_score === "number") {
    // registry_match_score is a 0–1 confidence value, not a 0–100
    // percentage — multiply before formatting, or a perfect match
    // displays as "1.0%" instead of "100.0%".
    rows.push([t("registryRecord.matchScore"), `${(check.registry_match_score * 100).toFixed(1)}%`]);
  }

  rows.push([t("registryRecord.signalUsed"), signalLabel]);
  rows.push([t("registryRecord.checked"), new Date(check.created_at).toLocaleString()]);

  return (
    <dl className="registry-record">
      {rows.map(([label, value]) => (
        <div className="registry-row" key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}
