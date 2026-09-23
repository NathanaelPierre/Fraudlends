import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import VerdictStamp from "../components/VerdictStamp";
import RegistryRecord from "../components/RegistryRecord";

export default function CheckDetail() {
  const { id } = useParams();
  const [check, setCheck] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getCheck(id)
      .then(setCheck)
      .catch((err) => setError(err.message));
  }, [id]);

  return (
    <>
      <div className="page-head">
        <Link to="/history" className="hint">
          ← Back to history
        </Link>
        <h1 style={{ marginTop: 10 }}>Case #{id}</h1>
      </div>

      {error && <div className="banner banner-risk">{error}</div>}

      {check && (
        <div className="check-grid">
          <div className="record-sheet check-form">
            <h3 style={{ marginBottom: 12 }}>Message checked</h3>
            <p className="message-text-block">{check.message_text}</p>
          </div>

          <div className="record-sheet result-card">
            <VerdictStamp verdict={check.overall_verdict} stampKey={check.id} />
            <p className="result-explanation">{check.ai_explanation}</p>
            <RegistryRecord check={check} />
          </div>
        </div>
      )}
    </>
  );
}
