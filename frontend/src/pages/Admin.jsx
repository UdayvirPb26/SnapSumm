import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../context/AuthContext';

export default function Admin() {
  const { logout } = useAuth();
  const [users, setUsers] = useState([]);
  const [error, setError] = useState('');

  const load = async () => {
    try {
      const data = await api.listUsers();
      setUsers(data.users || []);
    } catch (err) {
      setError(err.message || 'Failed to load users');
    }
  };

  useEffect(() => { load(); }, []);

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this user?')) return;
    try { await api.deleteUser(id); load(); }
    catch (err) { setError(err.message || 'Failed to delete user'); }
  };

  return (
    <div style={{ maxWidth: 980, margin: '0 auto', padding: '40px 24px 100px' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 30 }}>
        <div>
          <div style={{ fontSize: 11, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: 1.5, marginBottom: 10 }}>
            Admin dashboard
          </div>
          <h1 style={{ fontFamily: 'var(--ff-head)', fontSize: 36, fontWeight: 800 }}>Manage SnapSumm users</h1>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <Link className="btn btn-ghost" to="/">Home</Link>
          <button className="btn btn-ghost" onClick={logout}>Logout</button>
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 18, marginBottom: 32 }}>
        <div className="card">
          <strong style={{ display: 'block', fontSize: 32, color: 'var(--accent)', marginBottom: 8 }}>{users.length}</strong>
          <span style={{ fontSize: 13, color: 'var(--text2)' }}>Total users</span>
        </div>
        <div className="card">
          <strong style={{ display: 'block', fontSize: 20, marginBottom: 8 }}>Protected</strong>
          <span style={{ fontSize: 13, color: 'var(--text2)' }}>Admin account cannot be deleted</span>
        </div>
        <div className="card">
          <strong style={{ display: 'block', fontSize: 20, marginBottom: 8 }}>Secure</strong>
          <span style={{ fontSize: 13, color: 'var(--text2)' }}>Only admin users can access this page</span>
        </div>
      </div>

      <div className="card">
        <h2 style={{ fontFamily: 'var(--ff-head)', fontSize: 18, marginBottom: 18 }}>Registered users</h2>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead>
            <tr>
              {['ID', 'Username', 'Email', 'Joined', 'Actions'].map((h) => (
                <th key={h} style={{ padding: '14px 16px', textAlign: 'left', borderBottom: '1px solid var(--border)',
                  fontSize: 12, textTransform: 'uppercase', color: 'var(--text2)' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td style={cellStyle}>{u.id}</td>
                <td style={cellStyle}>{u.username}</td>
                <td style={cellStyle}>{u.email}</td>
                <td style={cellStyle}>{u.created_at ? u.created_at.slice(0, 10) : '—'}</td>
                <td style={cellStyle}>
                  {u.username.toLowerCase() !== 'admin'
                    ? <button className="btn btn-danger" onClick={() => handleDelete(u.id)}>Delete</button>
                    : <span style={{ fontSize: 12, color: 'var(--text2)' }}>Owner</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <p style={{ marginTop: 18, fontSize: 13, color: 'var(--text2)' }}>
          The first user to register with username <strong>admin</strong> becomes the single admin.
        </p>
      </div>
    </div>
  );
}

const cellStyle = { padding: '14px 16px', borderBottom: '1px solid var(--border)' };