import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import AuthLayout from "../components/AuthLayout";
import { api } from "../api/client";

export default function VerifyEmail() {
  const { t } = useTranslation();
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
      eyebrow={t("auth.verifyEyebrow")}
      title={t("auth.verifyTitle")}
      footer={
        <span>
          <Link to="/app">{t("auth.goToApp")}</Link>
        </span>
      }
    >
      {status === "checking" && <p>{t("auth.confirmingLink")}</p>}

      {status === "verified" && (
        <div className="banner banner-safe">{t("auth.emailVerified")}</div>
      )}

      {(status === "failed" || status === "missing") && (
        <>
          <div className="banner banner-risk">
            {status === "missing" ? t("auth.verifyLinkMissing") : error}
          </div>
          {!resent ? (
            <form onSubmit={handleResend} noValidate>
              <div className="field">
                <label htmlFor="resend-email">{t("auth.resendTo")}</label>
                <input
                  id="resend-email"
                  type="email"
                  required
                  value={resendEmail}
                  onChange={(e) => setResendEmail(e.target.value)}
                />
              </div>
              <button className="btn btn-pen btn-block" type="submit">
                {t("auth.resendVerification")}
              </button>
            </form>
          ) : (
            <p className="hint">{t("auth.resendSent")}</p>
          )}
        </>
      )}
    </AuthLayout>
  );
}
