import { useEffect, useState } from "react";
import { api } from "../../api/client";

const TABS = [
  { key: "audit", label: "Audit log" },
  { key: "logins", label: "Login attempts" },
];

export default function AdminSecurity() {
  const [tab, setTab] = useState("audit");
  const [rows, setRows] = useState([]);
  const [eventType, setEventType] = useState("");
  const [emailFilter, setEmailFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      if (tab === "audit") {
        const data = await api.adminAuditLog({ limit: 75, event_type: eventType || undefined, user_email: emailFilter || undefined });
        setRows(data);
      } else {
        const data = await api.adminLoginAttempts({ limit: 75, email: emailFilter || undefined });
        setRows(data);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  function handleSearch(e) {
    e.preventDefault();
    load();
  }

  return (
    <>
      <div className="page-head">
        <h1>Security</h1>
        <p>The audit trail and raw login history behind the live feed on Overview.</p>
      </div>

      <div className="filter-row" role="tablist" aria-label="Security view">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={tab === t.key}
            className={"filter-tab" + (tab === t.key ? " active" : "")}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <form className="inline-form admin-search-form" onSubmit={handleSearch}>
        {tab === "audit" && (
          <input
            type="text"
            placeholder="Filter by event type (e.g. login_failed)"
            value={eventType}
            onChange={(e) => setEventType(e.target.value)}
          />
        )}
        <input
          type="text"
          placeholder="Filter by email"
          value={emailFilter}
          onChange={(e) => setEmailFilter(e.target.value)}
        />
        <button className="btn btn-ghost" type="submit">
          Search
        </button>
      </form>

      {error && <div className="banner banner-risk">{error}</div>}

      {!loading && rows.length > 0 && tab === "audit" && (
        <div className="record-sheet ledger-table-wrap">
          <table className="ledger-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Event</th>
                <th>User</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td className="mono">{new Date(r.timestamp).toLocaleString()}</td>
                  <td className="mono">{r.event_type.replaceAll("_", " ")}</td>
                  <td>{r.user_email || (r.user_id ? `#${r.user_id}` : "—")}</td>
                  <td className="mono-text">{r.detail || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && rows.length > 0 && tab === "logins" && (
        <div className="record-sheet ledger-table-wrap">
          <table className="ledger-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Email</th>
                <th>Result</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td className="mono">{new Date(r.attempted_at).toLocaleString()}</td>
                  <td>{r.email}</td>
                  <td>
                    <span className={"status-tag" + (r.successful ? " safe" : " risk")}>
                      {r.successful ? "Success" : "Failed"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {loading && <p className="hint">Loading…</p>}
      {!loading && rows.length === 0 && !error && <div className="result-empty">Nothing matches these filters.</div>}
    </>
  );
}
