import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";

function Section({ title, description, children }) {
  return (
    <section className="settings-section record-sheet">
      <div className="settings-section-head">
        <h2>{title}</h2>
        {description && <p>{description}</p>}
      </div>
      <div className="settings-section-body">{children}</div>
    </section>
  );
}

export default function Settings() {
  const { t } = useTranslation();
  const { logout } = useAuth();
  const navigate = useNavigate();

  const [apiKeyStatus, setApiKeyStatus] = useState(null);
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [apiKeyMsg, setApiKeyMsg] = useState("");

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [passwordMsg, setPasswordMsg] = useState("");
  const [passwordErr, setPasswordErr] = useState("");

  const [sessionMsg, setSessionMsg] = useState("");

  const [auditLog, setAuditLog] = useState([]);

  const [deletePassword, setDeletePassword] = useState("");
  const [deleteErr, setDeleteErr] = useState("");
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  useEffect(() => {
    api.getApiKeyStatus().then(setApiKeyStatus).catch(() => {});
    api.getAuditLog({ limit: 15 }).then(setAuditLog).catch(() => {});
  }, []);

  async function handleSaveKey(e) {
    e.preventDefault();
    setApiKeyMsg("");
    try {
      const status = await api.saveApiKey(apiKeyInput);
      setApiKeyStatus(status);
      setApiKeyInput("");
      setApiKeyMsg(t("settings.keySaved"));
    } catch (err) {
      setApiKeyMsg(err.message);
    }
  }

  async function handleDeleteKey() {
    try {
      const status = await api.deleteApiKey();
      setApiKeyStatus(status);
      setApiKeyMsg(t("settings.keyRemoved"));
    } catch (err) {
      setApiKeyMsg(err.message);
    }
  }

  async function handleChangePassword(e) {
    e.preventDefault();
    setPasswordMsg("");
    setPasswordErr("");
    try {
      const res = await api.changePassword(currentPassword, newPassword);
      setPasswordMsg(res.detail);
      setCurrentPassword("");
      setNewPassword("");
      setTimeout(() => {
        logout();
        navigate("/login");
      }, 1500);
    } catch (err) {
      setPasswordErr(err.message);
    }
  }

  async function handleRevoke() {
    setSessionMsg("");
    try {
      const res = await api.revokeSessions();
      setSessionMsg(res.detail);
      setTimeout(() => {
        logout();
        navigate("/login");
      }, 1500);
    } catch (err) {
      setSessionMsg(err.message);
    }
  }

  async function handleDeleteAccount(e) {
    e.preventDefault();
    setDeleteErr("");
    if (!confirmingDelete) {
      setConfirmingDelete(true);
      return;
    }
    try {
      await api.deleteAccount(deletePassword);
      logout();
      navigate("/login");
    } catch (err) {
      setDeleteErr(err.message);
    }
  }

  return (
    <>
      <div className="page-head">
        <h1>{t("settings.title")}</h1>
        <p>{t("settings.intro")}</p>
      </div>

      <Section title={t("settings.aiKeyTitle")} description={t("settings.aiKeyDesc")}>
        {apiKeyStatus?.is_set ? (
          <div className="key-status-row">
            <span className="mono-text">{apiKeyStatus.masked_key}</span>
            <button className="btn btn-ghost" type="button" onClick={handleDeleteKey}>
              {t("settings.removeKey")}
            </button>
          </div>
        ) : (
          <form onSubmit={handleSaveKey} className="inline-form">
            <input
              type="password"
              placeholder={t("settings.keyPlaceholder")}
              value={apiKeyInput}
              onChange={(e) => setApiKeyInput(e.target.value)}
              minLength={10}
              maxLength={200}
              required
            />
            <button className="btn btn-pen" type="submit">
              {t("settings.saveKey")}
            </button>
          </form>
        )}
        {apiKeyMsg && <p className="hint" style={{ marginTop: 8 }}>{apiKeyMsg}</p>}
      </Section>

      <Section title={t("settings.changePasswordTitle")}>
        <form onSubmit={handleChangePassword}>
          {passwordErr && <div className="banner banner-risk">{passwordErr}</div>}
          {passwordMsg && <div className="banner banner-safe">{passwordMsg}</div>}
          <div className="field">
            <label htmlFor="current-password">{t("settings.currentPassword")}</label>
            <input
              id="current-password"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="new-password">{t("settings.newPassword")}</label>
            <input
              id="new-password"
              type="password"
              minLength={8}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
            />
          </div>
          <button className="btn btn-pen" type="submit">
            {t("settings.updatePassword")}
          </button>
        </form>
      </Section>

      <Section title={t("settings.sessionsTitle")} description={t("settings.sessionsDesc")}>
        {sessionMsg && <p className="hint" style={{ marginBottom: 10 }}>{sessionMsg}</p>}
        <button className="btn btn-ghost" type="button" onClick={handleRevoke}>
          {t("settings.logoutEverywhere")}
        </button>
      </Section>

      <Section title={t("settings.activityTitle")}>
        {auditLog.length === 0 ? (
          <p className="hint">{t("settings.noActivity")}</p>
        ) : (
          <ul className="audit-list">
            {auditLog.map((entry) => (
              <li key={entry.id}>
                <span className="mono-text">{new Date(entry.timestamp).toLocaleString()}</span>
                <span>{entry.event_type.replaceAll("_", " ")}</span>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title={t("settings.deleteTitle")} description={t("settings.deleteDesc")}>
        <form onSubmit={handleDeleteAccount}>
          {deleteErr && <div className="banner banner-risk">{deleteErr}</div>}
          {confirmingDelete && (
            <div className="field">
              <label htmlFor="delete-password">{t("settings.confirmPassword")}</label>
              <input
                id="delete-password"
                type="password"
                value={deletePassword}
                onChange={(e) => setDeletePassword(e.target.value)}
                required
                autoFocus
              />
            </div>
          )}
          <button className="btn btn-risk" type="submit">
            {confirmingDelete ? t("settings.deletePermanently") : t("settings.deleteAccount")}
          </button>
          {confirmingDelete && (
            <button
              className="btn btn-ghost"
              type="button"
              style={{ marginLeft: 8 }}
              onClick={() => setConfirmingDelete(false)}
            >
              {t("settings.cancel")}
            </button>
          )}
        </form>
      </Section>
    </>
  );
}
