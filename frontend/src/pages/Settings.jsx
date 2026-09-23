import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
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
      setApiKeyMsg("Saved.");
    } catch (err) {
      setApiKeyMsg(err.message);
    }
  }

  async function handleDeleteKey() {
    try {
      const status = await api.deleteApiKey();
      setApiKeyStatus(status);
      setApiKeyMsg("Removed.");
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
        <h1>Settings</h1>
        <p>Manage your account, sessions, and stored data.</p>
      </div>

      <Section
        title="AI provider key"
        description="Optional, for when the AI language-pattern layer is wired in. Stored encrypted; never shown again in full."
      >
        {apiKeyStatus?.is_set ? (
          <div className="key-status-row">
            <span className="mono-text">{apiKeyStatus.masked_key}</span>
            <button className="btn btn-ghost" type="button" onClick={handleDeleteKey}>
              Remove key
            </button>
          </div>
        ) : (
          <form onSubmit={handleSaveKey} className="inline-form">
            <input
              type="password"
              placeholder="Paste your API key"
              value={apiKeyInput}
              onChange={(e) => setApiKeyInput(e.target.value)}
              minLength={10}
              maxLength={200}
              required
            />
            <button className="btn btn-pen" type="submit">
              Save key
            </button>
          </form>
        )}
        {apiKeyMsg && <p className="hint" style={{ marginTop: 8 }}>{apiKeyMsg}</p>}
      </Section>

      <Section title="Change password">
        <form onSubmit={handleChangePassword}>
          {passwordErr && <div className="banner banner-risk">{passwordErr}</div>}
          {passwordMsg && <div className="banner banner-safe">{passwordMsg}</div>}
          <div className="field">
            <label htmlFor="current-password">Current password</label>
            <input
              id="current-password"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="new-password">New password</label>
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
            Update password
          </button>
        </form>
      </Section>

      <Section
        title="Sessions"
        description="Sign every device with a token for your account out at once, including this one."
      >
        {sessionMsg && <p className="hint" style={{ marginBottom: 10 }}>{sessionMsg}</p>}
        <button className="btn btn-ghost" type="button" onClick={handleRevoke}>
          Log out everywhere
        </button>
      </Section>

      <Section title="Recent account activity">
        {auditLog.length === 0 ? (
          <p className="hint">Nothing logged yet.</p>
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

      <Section
        title="Delete account"
        description="Permanently deletes your account, saved checks, and activity log. This can't be undone."
      >
        <form onSubmit={handleDeleteAccount}>
          {deleteErr && <div className="banner banner-risk">{deleteErr}</div>}
          {confirmingDelete && (
            <div className="field">
              <label htmlFor="delete-password">Confirm your password</label>
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
            {confirmingDelete ? "Permanently delete account" : "Delete account"}
          </button>
          {confirmingDelete && (
            <button
              className="btn btn-ghost"
              type="button"
              style={{ marginLeft: 8 }}
              onClick={() => setConfirmingDelete(false)}
            >
              Cancel
            </button>
          )}
        </form>
      </Section>
    </>
  );
}
