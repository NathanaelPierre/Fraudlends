const TONE = {
  safe: { cls: "safe", label: "Verified" },
  suspicious: { cls: "caution", label: "Unverified" },
  high_risk: { cls: "risk", label: "High risk" },
};

export default function StatusTag({ verdict }) {
  const t = TONE[verdict] || TONE.suspicious;
  return <span className={`status-tag ${t.cls}`}>{t.label}</span>;
}
