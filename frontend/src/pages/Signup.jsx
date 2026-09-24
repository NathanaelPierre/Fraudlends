import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import AuthLayout from "../components/AuthLayout";
import PasswordField from "../components/PasswordField";
import { useAuth } from "../context/AuthContext";

export default function Signup() {
  const { t } = useTranslation();
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [confirmError, setConfirmError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setConfirmError("");

    if (password.length < 8) {
      setError(t("auth.passwordMinLength"));
      return;
    }
    if (password !== confirmPassword) {
      setConfirmError(t("auth.passwordsDontMatch"));
      return;
    }

    setSubmitting(true);
    try {
      await signup(email, password);
      navigate("/app", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      eyebrow={t("auth.signupEyebrow")}
      title={t("auth.signupTitle")}
      footer={
        <span>
          {t("auth.alreadyHaveAccount")} <Link to="/login">{t("auth.login")}</Link>
        </span>
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

        <PasswordField
          id="password"
          label={t("auth.password")}
          value={password}
          onChange={(e) => {
            setPassword(e.target.value);
            if (confirmError) setConfirmError("");
          }}
          autoComplete="new-password"
          required
          minLength={8}
          hint={t("auth.atLeast8Chars")}
        />

        <PasswordField
          id="confirm_password"
          label={t("auth.confirmPassword")}
          value={confirmPassword}
          onChange={(e) => {
            setConfirmPassword(e.target.value);
            if (confirmError) setConfirmError("");
          }}
          autoComplete="new-password"
          required
          minLength={8}
          error={confirmError}
          hint={t("auth.reenterPassword")}
        />

        <button className="btn btn-pen btn-block" type="submit" disabled={submitting}>
          {submitting ? t("auth.creatingAccount") : t("auth.createAccountBtn")}
        </button>
      </form>
    </AuthLayout>
  );
}
