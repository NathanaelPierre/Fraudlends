import { useTranslation } from "react-i18next";

const STAMP_TONE = {
  safe: { tone: "safe", rotate: -3 },
  suspicious: { tone: "caution", rotate: 2 },
  high_risk: { tone: "risk", rotate: -2 },
};

export default function VerdictStamp({ verdict, stampKey }) {
  const { t } = useTranslation();
  const copy = STAMP_TONE[verdict] || STAMP_TONE.suspicious;
  const word = t(`verdict.${verdict}`, t("verdict.suspicious"));

  return (
    <div
      key={stampKey}
      className={`verdict-stamp tone-${copy.tone}`}
      style={{ "--stamp-rotate": `${copy.rotate}deg` }}
      role="status"
    >
      <span className="verdict-stamp-word">{word}</span>
    </div>
  );
}
