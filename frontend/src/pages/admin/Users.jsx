import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { useAuth } from "../../context/AuthContext";

export default function AdminUsers() {
  const { user: me } = useAuth();
  const [users, setUsers] = useState([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const rows = await api.adminListUsers({ limit: 100, q: q || undefined });
      setUsers(rows);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleSearch(e) {
    e.preventDefault();
    load();
  }

  async function toggleRole(u) {
    setBusyId(u.id);
    try {
      const nextRole = u.role === "admin" ? "user" : "admin";
      const updated = await api.adminSetRole(u.id, nextRole);
      setUsers((prev) => prev.map((row) => (row.id === u.id ? updated : row)));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  async function toggleActive(u) {
    setBusyId(u.id);
    try {
      const updated = u.is_active ? await api.adminSuspendUser(u.id) : await api.adminActivateUser(u.id);
      setUsers((prev) => prev.map((row) => (row.id === u.id ? updated : row)));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <>
      <div className="page-head">
        <h1>Users</h1>
        <p>Promote admins, suspend accounts. A suspension ends every active session immediately.</p>
      </div>

      <form className="inline-form admin-search-form" onSubmit={handleSearch}>
        <input type="text" placeholder="Search by email" value={q} onChange={(e) => setQ(e.target.value)} />
        <button className="btn btn-ghost" type="submit">
          Search
        </button>
      </form>

      {error && <div className="banner banner-risk">{error}</div>}

      {!loading && users.length > 0 && (
        <div className="record-sheet ledger-table-wrap">
          <table className="ledger-table">
            <thead>
              <tr>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>Checks</th>
                <th>High risk</th>
                <th>Last login</th>
                <th>Joined</th>
                <th aria-hidden="true"></th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.email}</td>
                  <td className="mono">{u.role}</td>
                  <td>
                    <span className={"status-tag" + (u.is_active ? " safe" : " risk")}>
                      {u.is_active ? "Active" : "Suspended"}
                    </span>
                  </td>
                  <td className="mono">{u.checks_count}</td>
                  <td className="mono">{u.high_risk_checks_count}</td>
                  <td className="mono">{u.last_login_at ? new Date(u.last_login_at).toLocaleString() : "—"}</td>
                  <td className="mono">{new Date(u.created_at).toLocaleDateString()}</td>
                  <td className="admin-row-actions">
                    <button
                      className="btn btn-ghost"
                      type="button"
                      disabled={busyId === u.id || u.id === me?.id}
                      title={u.id === me?.id ? "You can't change your own role" : undefined}
                      onClick={() => toggleRole(u)}
                    >
                      {u.role === "admin" ? "Demote" : "Promote"}
                    </button>
                    <button
                      className={"btn " + (u.is_active ? "btn-risk" : "btn-ghost")}
                      type="button"
                      disabled={busyId === u.id || u.id === me?.id}
                      title={u.id === me?.id ? "You can't suspend your own account" : undefined}
                      onClick={() => toggleActive(u)}
                    >
                      {u.is_active ? "Suspend" : "Reactivate"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {loading && <p className="hint">Loading…</p>}
      {!loading && users.length === 0 && !error && <div className="result-empty">No users match that search.</div>}
    </>
  );
}
