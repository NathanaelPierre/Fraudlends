import { useEffect, useState } from "react";
import { api } from "../../api/client";
import StatusTag from "../../components/StatusTag";

const VERDICT_FILTERS = [
  { value: "", label: "All" },
  { value: "safe", label: "Verified" },
  { value: "suspicious", label: "Unverified" },
  { value: "high_risk", label: "High risk" },
];

const PAGE_SIZE = 25;

export default function AdminCheckExplorer() {
  const [verdict, setVerdict] = useState("");
  const [userEmail, setUserEmail] = useState("");
  const [claimedSender, setClaimedSender] = useState("");
  const [checks, setChecks] = useState([]);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load(nextOffset, replace) {
    setLoading(true);
    setError("");
    try {
      const rows = await api.adminListChecks({
        limit: PAGE_SIZE,
        offset: nextOffset,
        verdict: verdict || undefined,
        user_email: userEmail || undefined,
        claimed_sender: claimedSender || undefined,
      });
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
    load(0, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [verdict]);

  function handleSearchSubmit(e) {
    e.preventDefault();
    load(0, true);
  }

  return (
    <>
      <div className="page-head">
        <h1>Checks</h1>
        <p>Every registry check submitted, across every user — the core investigation surface.</p>
      </div>

      <div className="filter-row" role="tablist" aria-label="Filter by verdict">
        {VERDICT_FILTERS.map((f) => (
          <button
            key={f.value}
            type="button"
            role="tab"
            aria-selected={verdict === f.value}
            className={"filter-tab" + (verdict === f.value ? " active" : "")}
            onClick={() => setVerdict(f.value)}
          >
            {f.label}
          </button>
        ))}
      </div>

      <form className="inline-form admin-search-form" onSubmit={handleSearchSubmit}>
        <input
          type="text"
          placeholder="Filter by user email"
          value={userEmail}
          onChange={(e) => setUserEmail(e.target.value)}
        />
        <input
          type="text"
          placeholder="Filter by claimed sender"
          value={claimedSender}
          onChange={(e) => setClaimedSender(e.target.value)}
        />
        <button className="btn btn-ghost" type="submit">
          Search
        </button>
      </form>

      {error && <div className="banner banner-risk">{error}</div>}

      {!loading && checks.length === 0 && !error && (
        <div className="result-empty">No checks match these filters.</div>
      )}

      {checks.length > 0 && (
        <div className="record-sheet ledger-table-wrap">
          <table className="ledger-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>User</th>
                <th>Claimed sender</th>
                <th>Registry</th>
                <th>Verdict</th>
                <th>Flags</th>
              </tr>
            </thead>
            <tbody>
              {checks.map((c) => (
                <tr key={c.id}>
                  <td className="mono">{new Date(c.created_at).toLocaleString()}</td>
                  <td className="mono">{c.user_email}</td>
                  <td>{c.claimed_sender || "—"}</td>
                  <td className="mono">{c.registry_match_status.replaceAll("_", " ")}</td>
                  <td>
                    <StatusTag verdict={c.overall_verdict} />
                  </td>
                  <td className="mono-text">{(c.ai_flags || []).join(", ") || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {loading && <p className="hint">Loading…</p>}

      {!loading && hasMore && checks.length > 0 && (
        <button className="btn btn-ghost" type="button" onClick={() => load(offset + PAGE_SIZE, false)}>
          Load more
        </button>
      )}
    </>
  );
}
