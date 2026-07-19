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

  useEffect(() => { load(); }, [refreshKey]);

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
    try { await api.renameSummary(id, title); } finally { load(); }
  };

  return (
    <>
      {isOpen && (
        <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 90 }} />
      )}
      <aside style={{
        position: 'fixed', top: 0, left: isOpen ? 0 : '-300px', width: 280, height: '100vh',
        background: 'var(--surface)', borderRight: '1px solid var(--border)', zIndex: 95,
        transition: 'left var(--transition)', display: 'flex', flexDirection: 'column', padding: 16,
      }}>
        <button className="btn btn-primary" style={{ marginBottom: 14 }} onClick={onNew}>+ New Summary</button>
        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
          {summaries.length === 0 && (
            <div style={{ color: 'var(--text2)', fontSize: 13, textAlign: 'center', marginTop: 40 }}>
              No summaries yet.<br />Create one to get started!
            </div>
          )}
          {summaries.map((s) => (
            <div key={s.id} onClick={() => onSelect(s.id)} title={s.title}
              style={{ position: 'relative', padding: '10px 34px 10px 12px', borderRadius: 8, cursor: 'pointer' }}
              onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--surface2)')}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}>
              {renamingId === s.id ? (
                <input autoFocus value={renameValue} onClick={(e) => e.stopPropagation()}
                  onChange={(e) => setRenameValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') confirmRename(s.id);
                    if (e.key === 'Escape') setRenamingId(null);
                  }}
                  onBlur={() => confirmRename(s.id)}
                  style={{ width: '100%', background: 'var(--surface2)', border: '1px solid var(--border2)', borderRadius: 6, color: 'var(--text)', padding: '4px 6px', fontSize: 13 }} />
              ) : (
                <div style={{ fontSize: 13, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.title}</div>
              )}
              <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 2 }}>{formatDate(s.created_at)}</div>
              <button onClick={(e) => startRename(s, e)} title="Rename"
                style={{ position: 'absolute', top: 8, right: 26, background: 'none', border: 'none', color: 'var(--text2)', cursor: 'pointer', fontSize: 13 }}>✎</button>
              <button onClick={(e) => handleDelete(s.id, e)} title="Delete"
                style={{ position: 'absolute', top: 8, right: 6, background: 'none', border: 'none', color: 'var(--text2)', cursor: 'pointer', fontSize: 13 }}>✕</button>
            </div>
          ))}
        </div>
      </aside>
    </>
  );
}