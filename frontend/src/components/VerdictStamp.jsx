const STAMP_COPY = {
  safe: { word: "Verified", tone: "safe", rotate: -3 },
  suspicious: { word: "Unverified", tone: "caution", rotate: 2 },
  high_risk: { word: "High risk", tone: "risk", rotate: -2 },
};

export default function VerdictStamp({ verdict, stampKey }) {
  const copy = STAMP_COPY[verdict] || STAMP_COPY.suspicious;

  return (
    <div
      key={stampKey}
      className={`verdict-stamp tone-${copy.tone}`}
      style={{ "--stamp-rotate": `${copy.rotate}deg` }}
      role="status"
    >
      <span className="verdict-stamp-word">{copy.word}</span>
    </div>
  );
}
