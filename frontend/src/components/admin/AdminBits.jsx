// Small shared bits for the admin console pages: a stat card, a
// pulsing "live" dot, and a formatter that turns a raw event-bus
// event into something readable in a feed.

export function StatCard({ label, value, sub, tone }) {
  return (
    <div className={"admin-stat-card" + (tone ? ` tone-${tone}` : "")}>
      <div className="admin-stat-value">{value}</div>
      <div className="admin-stat-label">{label}</div>
      {sub && <div className="admin-stat-sub">{sub}</div>}
    </div>
  );
}

export function LiveDot({ connected }) {
  return (
    <span className={"live-dot" + (connected ? " on" : "")} title={connected ? "Live" : "Reconnecting…"}>
      <span className="live-dot-core" />
      Live
    </span>
  );
}

const EVENT_COPY = {
  check_created: (d) => ({
    label: `Check submitted — ${d.claimed_sender || "no sender given"}`,
    tone: d.overall_verdict === "high_risk" ? "risk" : d.overall_verdict === "suspicious" ? "caution" : "safe",
    meta: `${d.email || "unknown user"} · ${(d.overall_verdict || "").replaceAll("_", " ")}${d.saved === false ? " · unsaved" : ""}`,
  }),
  rate_limit_hit: (d) => ({
    label: "Rate limit hit on /checks",
    tone: "caution",
    meta: d.email || `user #${d.user_id}`,
  }),
  admin_action: (d) => ({
    label: (d.action || "admin action").replaceAll("_", " "),
    tone: "pen",
    meta: `${d.target || ""}${d.by ? ` · by ${d.by}` : ""}`,
  }),
  audit: (d) => {
    const type = d.event_type || "event";
    const tone =
      type.includes("failed") || type.includes("lockout") || type.includes("blocked")
        ? "caution"
        : type.includes("suspend")
        ? "risk"
        : "pen";
    return { label: type.replaceAll("_", " "), tone, meta: d.detail || (d.user_id ? `user #${d.user_id}` : "") };
  },
};

export function describeEvent(event) {
  const fn = EVENT_COPY[event.type];
  if (fn) return fn(event.data || {});
  return { label: event.type, tone: "pen", meta: "" };
}

export function timeAgo(ts) {
  const seconds = Math.max(0, Math.floor(Date.now() / 1000 - ts));
  if (seconds < 5) return "just now";
  if (seconds < 60) return `${seconds}s ago`;
  const mins = Math.floor(seconds / 60);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}
