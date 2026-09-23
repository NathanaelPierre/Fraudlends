import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import StatusTag from "../components/StatusTag";

const FILTERS = [
  { value: "", label: "All" },
  { value: "safe", label: "Verified" },
  { value: "suspicious", label: "Unverified" },
  { value: "high_risk", label: "High risk" },
];

const PAGE_SIZE = 20;

export default function CaseLog() {
  const [filter, setFilter] = useState("");
  const [checks, setChecks] = useState([]);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load(nextOffset, nextFilter, replace) {
    setLoading(true);
    setError("");
    try {
      const rows = await api.listChecks({ limit: PAGE_SIZE, offset: nextOffset, verdict: nextFilter || undefined });
      setChecks((prev) => (replace ? rows : [...prev, ...rows]));
      setHasMore(rows.length === PAGE_SIZE);
      setOffset(nextOffset);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(0, filter, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  return (
    <>
      <div className="page-head">
        <h1>History</h1>
        <p>Every check you've chosen to save, most recent first.</p>
      </div>

      <div className="filter-row" role="tablist" aria-label="Filter by verdict">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            type="button"
            role="tab"
            aria-selected={filter === f.value}
            className={"filter-tab" + (filter === f.value ? " active" : "")}
            onClick={() => setFilter(f.value)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {error && <div className="banner banner-risk">{error}</div>}

      {!loading && checks.length === 0 && !error && (
        <div className="result-empty">
          Nothing here yet. Checks you save from Home will show up here in your history.
        </div>
      )}

      {checks.length > 0 && (
        <div className="record-sheet ledger-table-wrap">
          <table className="ledger-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Claimed sender</th>
                <th>Registry</th>
                <th>Verdict</th>
                <th aria-hidden="true"></th>
              </tr>
            </thead>
            <tbody>
              {checks.map((c) => (
                <tr key={c.id}>
                  <td className="mono">{new Date(c.created_at).toLocaleDateString()}</td>
                  <td>{c.claimed_sender || "—"}</td>
                  <td className="mono">{c.registry_match_status.replaceAll("_", " ")}</td>
                  <td>
                    <StatusTag verdict={c.overall_verdict} />
                  </td>
                  <td>
                    <Link to={`/history/${c.id}`}>View</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {loading && <p className="hint">Loading…</p>}

      {!loading && hasMore && checks.length > 0 && (
        <button className="btn btn-ghost" type="button" onClick={() => load(offset + PAGE_SIZE, filter, false)}>
          Load more
        </button>
      )}
    </>
  );
}
