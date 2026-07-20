import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const { login, continueAsGuest } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      await login(username, password);
      navigate('/');
    } catch (err) {
      setError(err.message || 'Invalid username or password');
    } finally {
      setSubmitting(false);
    }
  };

  const handleGuest = async () => {
    await continueAsGuest();
    navigate('/');
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex' }}>
      <div className="auth-left">
        <div className="demo-card">
          <div className="demo-topbar">
            <span className="demo-dot" />
            <span className="demo-dot" />
            <span className="demo-dot" />
            <span style={{
              marginLeft: 8, fontFamily: 'var(--ff-mono)', fontSize: 10, color: 'var(--text3)',
              background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 6, padding: '4px 10px',
            }}>
              youtube.com/watch?v=...
            </span>
          </div>
          <div className="demo-body">
            <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
              <div style={{
                flex: 1, padding: '10px 14px', background: 'var(--surface2)', border: '1px solid var(--border2)',
                borderRadius: 8, fontFamily: 'var(--ff-mono)', fontSize: 11, color: 'var(--text2)',
              }}>
                https://youtube.com/watch?v=...
              </div>
              <div style={{
                padding: '10px 16px', background: 'var(--accent-grad)', color: '#0d1000', borderRadius: 8,
                fontFamily: 'var(--ff-head)', fontSize: 11, fontWeight: 700, whiteSpace: 'nowrap',
              }}>
                Summarize →
              </div>
            </div>
            <div className="demo-line" style={{ width: '100%' }} />
            <div className="demo-line" style={{ width: '88%' }} />
            <div className="demo-line" style={{ width: '95%' }} />
            <div className="demo-line" style={{ width: '75%', marginBottom: 16 }} />
            <div style={{ fontFamily: 'var(--ff-mono)', fontSize: 9, color: 'var(--text3)', letterSpacing: 1.5, textTransform: 'uppercase', marginBottom: 10 }}>
              Key Points
            </div>
            {[80, 65, 75].map((w, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <div style={{
                  width: 18, height: 18, borderRadius: 4, background: 'var(--accent-dim)',
                  border: '1px solid rgba(240,118,69,0.2)', display: 'flex', alignItems: 'center',
                  justifyContent: 'center', fontSize: 8, color: 'var(--accent)', flexShrink: 0,
                }}>
                  {String(i + 1).padStart(2, '0')}
                </div>
                <div className="demo-line" style={{ width: `${w}%`, marginBottom: 0, flex: 1 }} />
              </div>
            ))}
          </div>
        </div>
        <div className="auth-headline">
          <h2>Turn hours into <span style={{ color: 'var(--accent)' }}>minutes.</span></h2>
          <p>Paste any YouTube URL and get a clean, accurate AI summary with key points.</p>
        </div>
      </div>

      <div className="auth-shell" style={{ flex: 1 }}>
        <div className="auth-box card fade-in">
          <h1>Sign in to your account</h1>
          <p className="sub">Enter your credentials to continue.</p>

          {error && <div className="error-banner">{error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="field">
              <label htmlFor="username">Username</label>
              <input
                id="username"
                type="text"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <button className="btn btn-primary" style={{ width: '100%' }} type="submit" disabled={submitting}>
              {submitting ? 'Signing in…' : 'Sign in →'}
            </button>
          </form>

          <button
            className="btn btn-ghost"
            style={{ width: '100%', marginTop: 12 }}
            onClick={handleGuest}
          >
            Continue as Guest
          </button>

          <div className="link-row">
            Don&apos;t have an account? <Link to="/register">Create one</Link>
          </div>
        </div>
      </div>
    </div>
  );
}