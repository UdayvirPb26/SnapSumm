import { useEffect, useState } from 'react';
import { api } from '../api';

function formatDate(isoDate) {
  const date = new Date(isoDate);
  const diffMs = new Date() - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);
  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// Persistent on desktop (always visible in the layout flow), slides in as an
// overlay on narrow screens (see .app-sidebar rules in theme.css).
export default function Sidebar({ isOpen, onClose, onSelect, onNew, refreshKey }) {
  const [summaries, setSummaries] = useState([]);
  const [renamingId, setRenamingId] = useState(null);
  const [renameValue, setRenameValue] = useState('');

  const load = async () => {
    try {
      const data = await api.listSummaries();
      setSummaries(data.summaries || []);
    } catch (err) {
      console.error('Error loading summaries:', err);
    }
  };

  useEffect(() => {
    load();
  }, [refreshKey]);

  const handleDelete = async (id, e) => {
    e.stopPropagation();
    if (!window.confirm('Delete this summary?')) return;
    await api.deleteSummary(id);
    load();
  };

  const startRename = (s, e) => {
    e.stopPropagation();
    setRenamingId(s.id);
    setRenameValue(s.title);
  };

  const confirmRename = async (id) => {
    const title = renameValue.trim();
    setRenamingId(null);
    if (!title) return;
    try {
      await api.renameSummary(id, title);
    } finally {
      load();
    }
  };

  return (
    <>
      {isOpen && <div className="sidebar-scrim" onClick={onClose} />}
      <aside className={`app-sidebar${isOpen ? ' open' : ''}`}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20, padding: '0 4px' }}>
          <div style={{
            width: 28, height: 28, background: 'var(--accent-grad)', borderRadius: 7,
            display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#0d1000', fontSize: 14, flexShrink: 0,
          }}>
            ▶
          </div>
          <strong style={{ fontFamily: 'var(--ff-head)', fontSize: 15 }}>
            Snap<span style={{ color: 'var(--accent)', fontWeight: 500 }}>Summ</span>
          </strong>
        </div>

        <button className="btn btn-primary" style={{ marginBottom: 16, width: '100%' }} onClick={onNew}>
          + New Summary
        </button>

        <div style={{ fontSize: 11, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: 1, padding: '0 4px', marginBottom: 8 }}>
          History
        </div>

        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 4 }}>
          {summaries.length === 0 && (
            <div style={{ color: 'var(--text2)', fontSize: 13, textAlign: 'center', marginTop: 30, padding: '0 10px' }}>
              📝 No summaries yet.<br />Create one to get started!
            </div>
          )}
          {summaries.map((s) => (
            <div
              key={s.id}
              onClick={() => onSelect(s.id)}
              title={s.title}
              className="fade-in"
              style={{
                position: 'relative', padding: '10px 56px 10px 12px', borderRadius: 8,
                cursor: 'pointer',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--surface2)')}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
            >
              {renamingId === s.id ? (
                <input
                  autoFocus
                  value={renameValue}
                  onClick={(e) => e.stopPropagation()}
                  onChange={(e) => setRenameValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') confirmRename(s.id);
                    if (e.key === 'Escape') setRenamingId(null);
                  }}
                  onBlur={() => confirmRename(s.id)}
                  style={{
                    width: '100%', background: 'var(--surface2)', border: '1px solid var(--border2)',
                    borderRadius: 6, color: 'var(--text)', padding: '4px 6px', fontSize: 13,
                  }}
                />
              ) : (
                <div style={{ fontSize: 13, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {s.title}
                </div>
              )}
              <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 2 }}>{formatDate(s.created_at)}</div>
              <button
                onClick={(e) => startRename(s, e)}
                title="Rename"
                style={{
                  position: 'absolute', top: 8, right: 30, background: 'none', border: 'none',
                  color: 'var(--text2)', cursor: 'pointer', fontSize: 13, padding: 4,
                }}
              >
                ✎
              </button>
              <button
                onClick={(e) => handleDelete(s.id, e)}
                title="Delete"
                style={{
                  position: 'absolute', top: 8, right: 8, background: 'none', border: 'none',
                  color: 'var(--text2)', cursor: 'pointer', fontSize: 13, padding: 4,
                }}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      </aside>
    </>
  );
}