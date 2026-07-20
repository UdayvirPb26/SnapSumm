import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({ username: '', email: '', password: '', confirmPassword: '' });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (form.password !== form.confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    if (form.password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    setSubmitting(true);
    try {
      await register(form.username, form.email, form.password, form.confirmPassword);
      navigate('/login');
    } catch (err) {
      setError(err.message || 'Registration failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex' }}>
      <div className="auth-left">
        <div className="demo-card">
          <div className="demo-topbar">
            <span className="demo-dot" />
            <span className="demo-dot" />
            <span className="demo-dot" />
          </div>
          <div className="demo-body">
            <div style={{ fontFamily: 'var(--ff-mono)', fontSize: 9, color: 'var(--text3)', letterSpacing: 1.5, textTransform: 'uppercase', marginBottom: 14 }}>
              Your history, saved
            </div>
            {['Building AI Summarizers', 'React Tutorial 2026', 'Learn Flask in 30 Minutes'].map((title, i) => (
              <div key={title} style={{
                display: 'flex', alignItems: 'center', gap: 10, padding: '10px 0',
                borderBottom: i < 2 ? '1px solid var(--border)' : 'none',
              }}>
                <div style={{
                  width: 34, height: 34, borderRadius: 6, background: 'var(--accent-grad)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#0d1000',
                  fontSize: 14, flexShrink: 0,
                }}>
                  ▶
                </div>
                <div style={{ fontSize: 12, color: 'var(--text2)' }}>{title}</div>
              </div>
            ))}
          </div>
        </div>
        <div className="auth-headline">
          <h2>Your summaries, <span style={{ color: 'var(--accent)' }}>always saved.</span></h2>
          <p>Create an account to keep a searchable history of every video you summarize.</p>
        </div>
      </div>

      <div className="auth-shell" style={{ flex: 1 }}>
        <div className="auth-box card fade-in">
          <h1>Create your account</h1>
          <p className="sub">Start summarizing YouTube videos in seconds.</p>

          {error && <div className="error-banner">{error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="field">
              <label htmlFor="username">Username</label>
              <input id="username" type="text" value={form.username} onChange={update('username')} required />
            </div>
            <div className="field">
              <label htmlFor="email">Email</label>
              <input id="email" type="email" value={form.email} onChange={update('email')} required />
            </div>
            <div className="field">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                value={form.password}
                onChange={update('password')}
                minLength={6}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="confirmPassword">Confirm password</label>
              <input
                id="confirmPassword"
                type="password"
                value={form.confirmPassword}
                onChange={update('confirmPassword')}
                required
              />
            </div>
            <button className="btn btn-primary" style={{ width: '100%' }} type="submit" disabled={submitting}>
              {submitting ? 'Creating account…' : 'Create account →'}
            </button>
          </form>

          <div className="link-row">
            Already have an account? <Link to="/login">Sign in</Link>
          </div>
        </div>
      </div>
    </div>
  );
}