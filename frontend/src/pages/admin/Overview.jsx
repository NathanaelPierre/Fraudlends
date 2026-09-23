import { useEffect, useRef, useState } from "react";
import { api, subscribeAdminStream } from "../../api/client";
import { StatCard, LiveDot, describeEvent, timeAgo } from "../../components/admin/AdminBits";

const POLL_MS = 6000;

export default function AdminOverview() {
  const [overview, setOverview] = useState(null);
  const [error, setError] = useState("");
  const [events, setEvents] = useState([]);
  const [connected, setConnected] = useState(false);
  const [, forceTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await api.adminOverview();
        if (!cancelled) {
          setOverview(data);
          setError("");
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }
    load();
    const id = setInterval(load, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  useEffect(() => {
    const close = subscribeAdminStream(
      (event) => {
        setConnected(true);
        setEvents((prev) => [event, ...prev].slice(0, 40));
      },
      () => setConnected(false)
    );
    return close;
  }, []);

  // Re-render every 15s purely so "X ago" labels stay fresh without a
  // per-event timer.
  useEffect(() => {
    const id = setInterval(() => forceTick((n) => n + 1), 15000);
    return () => clearInterval(id);
  }, []);

  const verdicts = overview?.verdict_breakdown || {};
  const verdicts24h = overview?.verdict_breakdown_24h || {};
  const totalVerdicts = Object.values(verdicts).reduce((a, b) => a + b, 0) || 1;

  return (
    <>
      <div className="page-head admin-page-head">
        <div>
          <h1>Overview</h1>
          <p>System-wide status — refreshes every few seconds, security feed streams live.</p>
        </div>
        <LiveDot connected={connected} />
      </div>

      {error && <div className="banner banner-risk">{error}</div>}

      {overview && (
        <>
          <div className="admin-stat-grid">
            <StatCard label="Users" value={overview.users_total} sub={`${overview.admins_total} admin${overview.admins_total === 1 ? "" : "s"}`} />
            <StatCard
              label="Suspended"
              value={overview.users_suspended}
              tone={overview.users_suspended > 0 ? "caution" : undefined}
            />
            <StatCard label="Checks total" value={overview.checks_total} sub={`${overview.checks_last_24h} in last 24h`} />
            <StatCard
              label="High risk (24h)"
              value={verdicts24h.high_risk || 0}
              tone={(verdicts24h.high_risk || 0) > 0 ? "risk" : undefined}
            />
            <StatCard
              label="Failed logins (24h)"
              value={overview.failed_logins_last_24h}
              tone={overview.failed_logins_last_24h > 0 ? "caution" : undefined}
            />
            <StatCard
              label="Active lockouts"
              value={overview.active_lockouts}
              tone={overview.active_lockouts > 0 ? "risk" : undefined}
            />
            <StatCard label="Registry entities" value={overview.registry_entities_total} />
            <StatCard
              label="Uptime"
              value={formatUptime(overview.uptime_seconds)}
              sub={`since ${new Date(overview.server_started_at).toLocaleString()}`}
            />
          </div>

          <div className="admin-grid-2">
            <section className="record-sheet admin-panel">
              <div className="settings-section-head">
                <h2>Verdicts (all time)</h2>
              </div>
              <div className="verdict-bar-list">
                {["safe", "suspicious", "high_risk"].map((v) => (
                  <div className="verdict-bar-row" key={v}>
                    <span className="verdict-bar-label">{v.replaceAll("_", " ")}</span>
                    <div className="verdict-bar-track">
                      <div
                        className={`verdict-bar-fill tone-${v === "safe" ? "safe" : v === "suspicious" ? "caution" : "risk"}`}
                        style={{ width: `${((verdicts[v] || 0) / totalVerdicts) * 100}%` }}
                      />
                    </div>
                    <span className="verdict-bar-count">{verdicts[v] || 0}</span>
                  </div>
                ))}
              </div>
            </section>

            <section className="record-sheet admin-panel">
              <div className="settings-section-head">
                <h2>Since server start</h2>
                <p>Live event counters — reset on restart, not a historical total.</p>
              </div>
              <ul className="kv-list">
                {Object.entries(overview.live_event_counters).length === 0 && (
                  <li className="hint">No events yet.</li>
                )}
                {Object.entries(overview.live_event_counters).map(([k, v]) => (
                  <li key={k}>
                    <span className="mono-text">{k.replaceAll("_", " ")}</span>
                    <span>{v}</span>
                  </li>
                ))}
              </ul>
            </section>
          </div>
        </>
      )}

      <section className="record-sheet admin-panel admin-feed">
        <div className="settings-section-head">
          <h2>Live security feed</h2>
          <p>Every login, signup, check, and admin action, as it happens.</p>
        </div>
        {events.length === 0 && <p className="hint">Waiting for activity…</p>}
        <ul className="admin-feed-list">
          {events.map((event, i) => {
            const { label, tone, meta } = describeEvent(event);
            return (
              <li key={`${event.ts}-${i}`} className={`admin-feed-item tone-${tone}`}>
                <span className="admin-feed-dot" />
                <div className="admin-feed-body">
                  <span className="admin-feed-label">{label}</span>
                  {meta && <span className="admin-feed-meta">{meta}</span>}
                </div>
                <span className="admin-feed-time mono-text">{timeAgo(event.ts)}</span>
              </li>
            );
          })}
        </ul>
      </section>
    </>
  );
}

function formatUptime(seconds) {
  if (!seconds && seconds !== 0) return "—";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}
