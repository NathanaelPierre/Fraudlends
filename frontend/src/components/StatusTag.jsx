import { useTranslation } from "react-i18next";

const TONE = {
  safe: "safe",
  suspicious: "caution",
  high_risk: "risk",
};

export default function StatusTag({ verdict }) {
  const { t } = useTranslation();
  const cls = TONE[verdict] || TONE.suspicious;
  const label = t(`verdict.${verdict}`, t("verdict.suspicious"));
  return <span className={`status-tag ${cls}`}>{label}</span>;
}
