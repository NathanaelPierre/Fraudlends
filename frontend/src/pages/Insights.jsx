import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation, Trans } from "react-i18next";
import { api } from "../api/client";

// A dashboard rollup of the current user's own check history — total
// counts by verdict, feedback given so far, and which claimed senders
// have been checked most often. Backed entirely by GET /checks/summary,
// which is already scoped to the current user only.
export default function Insights() {
  const { t } = useTranslation();
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getChecksSummary()
      .then(setSummary)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <div className="page-head">
        <h1>{t("insights.title")}</h1>
        <p>{t("insights.intro")}</p>
      </div>

      {error && <div className="banner banner-risk">{error}</div>}
      {loading && <p className="hint">{t("history.loading")}</p>}

      {summary && !loading && (
        <>
          {summary.total_checks === 0 ? (
            <div className="result-empty">
              {t("insights.empty")}{" "}
              <Link to="/app">{t("insights.checkFirst")}</Link> {t("insights.toSeeInsights")}
            </div>
          ) : (
            <>
              <div className="insights-stat-grid">
                <div className="record-sheet insights-stat-card">
                  <div className="insights-stat-value">{summary.total_checks}</div>
                  <div className="insights-stat-label">{t("insights.totalChecks")}</div>
                </div>
                <div className="record-sheet insights-stat-card tone-safe">
                  <div className="insights-stat-value">{summary.safe_count}</div>
                  <div className="insights-stat-label">{t("insights.verified")}</div>
                </div>
                <div className="record-sheet insights-stat-card tone-caution">
                  <div className="insights-stat-value">{summary.suspicious_count}</div>
                  <div className="insights-stat-label">{t("insights.unverified")}</div>
                </div>
                <div className="record-sheet insights-stat-card tone-risk">
                  <div className="insights-stat-value">{summary.high_risk_count}</div>
                  <div className="insights-stat-label">{t("insights.highRisk")}</div>
                </div>
              </div>

              {summary.checks_with_feedback > 0 && (
                <div className="record-sheet insights-feedback-card">
                  <h3>{t("insights.yourFeedback")}</h3>
                  <p>
                    <Trans
                      i18nKey="insights.feedbackSummary"
                      count={summary.checks_with_feedback}
                      values={{
                        count: summary.checks_with_feedback,
                        correct: summary.feedback_marked_correct,
                        incorrect: summary.feedback_marked_incorrect,
                      }}
                      components={{ bold: <strong /> }}
                    />
                  </p>
                </div>
              )}

              {summary.most_checked_senders.length > 0 && (
                <div className="record-sheet insights-senders-card">
                  <h3>{t("insights.mostCheckedSenders")}</h3>
                  <table className="ledger-table">
                    <thead>
                      <tr>
                        <th>{t("insights.colSender")}</th>
                        <th>{t("insights.colCount")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {summary.most_checked_senders.map((row) => (
                        <tr key={row.sender}>
                          <td>{row.sender}</td>
                          <td>{row.count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </>
      )}
    </>
  );
}
