import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import AuthLayout from "../components/AuthLayout";
import { api } from "../api/client";

export default function ForgotPassword() {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await api.requestPasswordReset(email);
      setSent(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      eyebrow={t("auth.forgotEyebrow")}
      title={t("auth.forgotTitle")}
      footer={
        <span>
          <Link to="/login">{t("auth.backToLogin")}</Link>
        </span>
      }
    >
      {sent ? (
        <div className="banner banner-safe">{t("auth.resetLinkSent")}</div>
      ) : (
        <form onSubmit={handleSubmit} noValidate>
          {error && <div className="banner banner-risk">{error}</div>}
          <div className="field">
            <label htmlFor="email">{t("auth.email")}</label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <button className="btn btn-pen btn-block" type="submit" disabled={submitting}>
            {submitting ? t("auth.sending") : t("auth.sendResetLink")}
          </button>
        </form>
      )}
    </AuthLayout>
  );
}
