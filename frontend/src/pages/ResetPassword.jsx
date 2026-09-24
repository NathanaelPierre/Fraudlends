import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import AuthLayout from "../components/AuthLayout";
import { api } from "../api/client";

export default function ResetPassword() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    if (!token) {
      setError(t("auth.resetTokenMissing"));
      return;
    }
    setSubmitting(true);
    try {
      await api.confirmPasswordReset(token, password);
      setDone(true);
      setTimeout(() => navigate("/login", { replace: true }), 1800);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      eyebrow={t("auth.resetEyebrow")}
      title={t("auth.resetTitle")}
      footer={
        <span>
          <Link to="/login">{t("auth.backToLogin")}</Link>
        </span>
      }
    >
      {done ? (
        <div className="banner banner-safe">{t("auth.passwordUpdated")}</div>
      ) : (
        <form onSubmit={handleSubmit} noValidate>
          {error && <div className="banner banner-risk">{error}</div>}
          <div className="field">
            <label htmlFor="password">{t("auth.newPassword")}</label>
            <input
              id="password"
              type="password"
              autoComplete="new-password"
              minLength={8}
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <span className="hint">{t("auth.atLeast8Chars")}</span>
          </div>
          <button className="btn btn-pen btn-block" type="submit" disabled={submitting}>
            {submitting ? t("auth.updating") : t("auth.updatePassword")}
          </button>
        </form>
      )}
    </AuthLayout>
  );
}
