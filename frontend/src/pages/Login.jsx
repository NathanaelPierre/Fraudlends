import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import AuthLayout from "../components/AuthLayout";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const from = location.state?.from || "/app";

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      eyebrow={t("auth.loginEyebrow")}
      title={t("auth.loginTitle")}
      footer={
        <>
          <span>
            {t("auth.newHere")} <Link to="/signup">{t("auth.createAccount")}</Link>
          </span>
          <span>
            <Link to="/forgot-password">{t("auth.forgotPassword")}</Link>
          </span>
        </>
      }
    >
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

        <div className="field">
          <label htmlFor="password">{t("auth.password")}</label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>

        <button className="btn btn-pen btn-block" type="submit" disabled={submitting}>
          {submitting ? t("auth.loggingIn") : t("auth.login")}
        </button>
      </form>
    </AuthLayout>
  );
}
