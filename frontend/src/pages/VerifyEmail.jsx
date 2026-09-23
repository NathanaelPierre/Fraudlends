import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import AuthLayout from "../components/AuthLayout";
import { api } from "../api/client";

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";
  const [status, setStatus] = useState(token ? "checking" : "missing");
  const [error, setError] = useState("");
  const [resendEmail, setResendEmail] = useState("");
  const [resent, setResent] = useState(false);

  useEffect(() => {
    if (!token) return;
    api
      .confirmEmailVerification(token)
      .then(() => setStatus("verified"))
      .catch((err) => {
        setStatus("failed");
        setError(err.message);
      });
  }, [token]);

  async function handleResend(e) {
    e.preventDefault();
    try {
      await api.resendEmailVerification(resendEmail);
      setResent(true);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <AuthLayout
      eyebrow="Email verification"
      title="Confirming your email"
      footer={
        <span>
          <Link to="/app">Go to CipherLab</Link>
        </span>
      }
    >
      {status === "checking" && <p>Confirming your link…</p>}

      {status === "verified" && (
        <div className="banner banner-safe">Your email is verified.</div>
      )}

      {(status === "failed" || status === "missing") && (
        <>
          <div className="banner banner-risk">
            {status === "missing"
              ? "This page needs a verification link with a token."
              : error}
          </div>
          {!resent ? (
            <form onSubmit={handleResend} noValidate>
              <div className="field">
                <label htmlFor="resend-email">Resend the link to</label>
                <input
                  id="resend-email"
                  type="email"
                  required
                  value={resendEmail}
                  onChange={(e) => setResendEmail(e.target.value)}
                />
              </div>
              <button className="btn btn-pen btn-block" type="submit">
                Resend verification email
              </button>
            </form>
          ) : (
            <p className="hint">If that account exists and isn't verified, a new link is on its way.</p>
          )}
        </>
      )}
    </AuthLayout>
  );
}
