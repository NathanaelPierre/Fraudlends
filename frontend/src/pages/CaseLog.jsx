import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import StatusTag from "../components/StatusTag";

const PAGE_SIZE = 20;

export default function CaseLog() {
  const { t } = useTranslation();
  const FILTERS = [
    { value: "", labelKey: "history.filterAll" },
    { value: "safe", labelKey: "history.filterSafe" },
    { value: "suspicious", labelKey: "history.filterSuspicious" },
    { value: "high_risk", labelKey: "history.filterHighRisk" },
  ];

  const [filter, setFilter] = useState("");
  const [checks, setChecks] = useState([]);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [exporting, setExporting] = useState(false);

  async function handleExport() {
    setExporting(true);
    try {
      await api.exportChecksCsv();
    } catch (err) {
      setError(err.message);
    } finally {
      setExporting(false);
    }
  }

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
        <h1>{t("history.title")}</h1>
        <p>{t("history.intro")}</p>
        <button className="btn btn-ghost" type="button" onClick={handleExport} disabled={exporting}>
          {exporting ? t("history.exporting") : t("history.exportCsv")}
        </button>
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
            {t(f.labelKey)}
          </button>
        ))}
      </div>

      {error && <div className="banner banner-risk">{error}</div>}

      {!loading && checks.length === 0 && !error && (
        <div className="result-empty">{t("history.empty")}</div>
      )}

      {checks.length > 0 && (
        <div className="record-sheet ledger-table-wrap">
          <table className="ledger-table">
            <thead>
              <tr>
                <th>{t("history.colDate")}</th>
                <th>{t("history.colSender")}</th>
                <th>{t("history.colRegistry")}</th>
                <th>{t("history.colVerdict")}</th>
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
                    <Link to={`/history/${c.id}`}>{t("history.view")}</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {loading && <p className="hint">{t("history.loading")}</p>}

      {!loading && hasMore && checks.length > 0 && (
        <button className="btn btn-ghost" type="button" onClick={() => load(offset + PAGE_SIZE, filter, false)}>
          {t("history.loadMore")}
        </button>
      )}
    </>
  );
}
