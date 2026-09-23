const STATUS_LABEL = {
  verified: "Matched in registry",
  not_found: "Not found in registry",
  name_mismatch: "Close match, not exact",
  no_sender_given: "No sender given",
  registry_unavailable: "Registry unavailable",
};

export default function RegistryRecord({ check }) {
  const rows = [
    ["Claimed sender", check.claimed_sender || "—"],
    ["Registry status", STATUS_LABEL[check.registry_match_status] || check.registry_match_status],
  ];

  if (check.registry_matched_entity) {
    rows.push(["Closest registry entity", check.registry_matched_entity]);
  }
  if (typeof check.registry_match_score === "number") {
    rows.push(["Match score", `${check.registry_match_score.toFixed(1)}%`]);
  }

  rows.push(["Signal used", check.explanation_source === "ai" ? "Registry + AI" : "Registry only"]);
  rows.push(["Checked", new Date(check.created_at).toLocaleString()]);

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
