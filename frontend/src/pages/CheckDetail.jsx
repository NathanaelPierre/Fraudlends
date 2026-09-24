import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import VerdictStamp from "../components/VerdictStamp";
import RegistryRecord from "../components/RegistryRecord";
import EvidenceList from "../components/EvidenceList";

export default function CheckDetail() {
  const { t } = useTranslation();
  const { id } = useParams();
  const [check, setCheck] = useState(null);
  const [error, setError] = useState("");
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);

  useEffect(() => {
    api
      .getCheck(id)
      .then(setCheck)
      .catch((err) => setError(err.message));
  }, [id]);

  async function submitFeedback(isCorrect) {
    setFeedbackSubmitting(true);
    try {
      const updated = await api.submitCheckFeedback(id, isCorrect);
      setCheck(updated);
    } catch (err) {
      setError(err.message);
    } finally {
      setFeedbackSubmitting(false);
    }
  }

  return (
    <>
      <div className="page-head">
        <Link to="/history" className="hint">
          {t("checkDetail.back")}
        </Link>
        <h1 style={{ marginTop: 10 }}>{t("checkDetail.caseNumber", { id })}</h1>
      </div>

      {error && <div className="banner banner-risk">{error}</div>}

      {check && (
        <div className="check-grid">
          <div className="record-sheet check-form">
            <h3 style={{ marginBottom: 12 }}>{t("checkDetail.messageChecked")}</h3>
            <p className="message-text-block">{check.message_text}</p>
          </div>

          <div className="record-sheet result-card">
            <VerdictStamp verdict={check.overall_verdict} stampKey={check.id} />
            <p className="result-explanation">{check.ai_explanation}</p>
            {check.repeat_sender_summary && (
              <p className="hint repeat-sender-note">{check.repeat_sender_summary}</p>
            )}
            <RegistryRecord check={check} />
            <EvidenceList evidence={check.evidence} />

            <div className="feedback-row">
              <span className="hint">{t("checkDetail.feedbackQuestion")}</span>
              <button
                type="button"
                className={"btn btn-ghost" + (check.user_feedback === "correct" ? " active" : "")}
                disabled={feedbackSubmitting}
                onClick={() => submitFeedback(true)}
              >
                {t("checkDetail.feedbackYes")}
              </button>
              <button
                type="button"
                className={"btn btn-ghost" + (check.user_feedback === "incorrect" ? " active" : "")}
                disabled={feedbackSubmitting}
                onClick={() => submitFeedback(false)}
              >
                {t("checkDetail.feedbackNo")}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
