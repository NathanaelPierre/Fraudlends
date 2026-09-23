import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import VerdictStamp from "../components/VerdictStamp";
import RegistryRecord from "../components/RegistryRecord";
import { PENDING_MESSAGE_KEY } from "./LandingPage";

const EXAMPLE_MESSAGE =
  "Dear customer, your MCB internet banking access will be suspended today. Verify your account now and share the OTP sent to your phone to avoid suspension.";

export default function Check() {
  const [messageText, setMessageText] = useState("");
  const [saveCheck, setSaveCheck] = useState(true);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [stampKey, setStampKey] = useState(0);

  useEffect(() => {
    const pending = sessionStorage.getItem(PENDING_MESSAGE_KEY);
    if (pending) {
      setMessageText(pending);
      sessionStorage.removeItem(PENDING_MESSAGE_KEY);
    }
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const check = await api.createCheck({
        message_text: messageText,
        claimed_sender: null,
        save_check: saveCheck,
      });
      setResult(check);
      setStampKey((k) => k + 1);
    } catch (err) {
      setResult(null);
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  function fillExample() {
    setMessageText(EXAMPLE_MESSAGE);
  }

  return (
    <div className="check-page-center">
      <div className="page-head page-head-center">
        <h1>Check a message</h1>
        <p>
          Paste the message below. Klaro checks any sender it names against the Bank of Mauritius
          registry snapshot and tells you what it finds — a checkable fact, not a guess.
        </p>
      </div>

      <div className="check-grid">
        <form className="record-sheet check-form" onSubmit={handleSubmit} noValidate>
          <div className="field">
            <label htmlFor="message_text">The message</label>
            <textarea
              id="message_text"
              rows={8}
              required
              maxLength={5000}
              placeholder="Paste the SMS, email or WhatsApp text here…"
              value={messageText}
              onChange={(e) => setMessageText(e.target.value)}
            />
            <span className="hint">{messageText.length}/5000</span>
          </div>

          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={saveCheck}
              onChange={(e) => setSaveCheck(e.target.checked)}
            />
            <span>
              Save this check to my history. Turn this off if the message contains an OTP,
              account number, or anything you'd rather Klaro never store.
            </span>
          </label>

          {error && <div className="banner banner-risk">{error}</div>}

          <div className="check-form-actions">
            <button className="btn btn-pen" type="submit" disabled={submitting || !messageText.trim()}>
              {submitting ? "Checking…" : "Check this message"}
            </button>
            <button className="btn btn-ghost" type="button" onClick={fillExample}>
              Try an example
            </button>
          </div>
        </form>

        <div className="check-result">
          {!result && !submitting && (
            <div className="result-empty">
              <p>Your result will appear here — a verdict stamp, the registry match, and why.</p>
            </div>
          )}

          {submitting && <div className="result-empty">Checking against the registry…</div>}

          {result && !submitting && (
            <div className="record-sheet result-card">
              <VerdictStamp verdict={result.overall_verdict} stampKey={stampKey} />
              <p className="result-explanation">{result.ai_explanation}</p>
              <RegistryRecord check={result} />
              {result.id === 0 && (
                <p className="hint result-unsaved">Not saved — this check isn't in your history.</p>
              )}
              {result.id !== 0 && (
                <Link className="btn btn-ghost" to={`/history/${result.id}`}>
                  View in history
                </Link>
              )}
            </div>
          )}
        </div>
      </div>

      <p className="responsible-use-note">
        A registry match confirms a claimed sender's name is in a dated snapshot — it doesn't
        confirm the message itself is genuine. A sender that isn't found isn't proof of fraud
        either; many legitimate senders sit outside this registry entirely. Before sending money
        or sharing credentials, verify through the institution's own official channels, never a
        number or link inside the message you're checking.
      </p>
    </div>
  );
}
