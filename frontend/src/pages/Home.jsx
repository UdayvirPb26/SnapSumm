import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../api';
import Sidebar from '../components/Sidebar';

const LANGUAGES = { hi: 'Hindi', pa: 'Punjabi', bn: 'Bengali', ta: 'Tamil', te: 'Telugu' };

function extractVideoId(url) {
  const m = url.match(/(?:v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/);
  return m ? m[1] : null;
}

export default function Home() {
  const { user, logout } = useAuth();
  const isGuest = !!user?.is_guest;

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [tab, setTab] = useState(0);
  const [data, setData] = useState(null);
  const [displaySummary, setDisplaySummary] = useState('');
  const [originalSummary, setOriginalSummary] = useState('');
  const [isTranslated, setIsTranslated] = useState(false);
  const [translating, setTranslating] = useState(false);
  const [lang, setLang] = useState('hi');
  const [saving, setSaving] = useState(false);
  const [alreadySaved, setAlreadySaved] = useState(false);
  const urlInputRef = useRef(null);

  const resetAll = () => {
    setData(null); setDisplaySummary(''); setOriginalSummary('');
    setIsTranslated(false); setUrl(''); setError(''); setSuccess('');
    setAlreadySaved(false); setTab(0);
  };

  const handleNewSummary = () => { setSidebarOpen(false); resetAll(); };

  const handleSelectSummary = async (id) => {
    setSidebarOpen(false);
    try {
      const s = await api.getSummary(id);
      setData(s); setUrl(s.url || ''); setDisplaySummary(s.summary);
      setOriginalSummary(s.summary); setIsTranslated(false); setAlreadySaved(true);
      setError(''); setTab(0);
    } catch (err) {
      setError(err.message || 'Failed to load summary');
    }
  };

  const handleSummarize = async (e) => {
    e.preventDefault();
    if (!url.trim()) { urlInputRef.current?.focus(); return; }
    setError(''); setSuccess(''); setData(null); setLoading(true);
    try {
      const result = await api.summarize(url.trim());
      setData(result); setDisplaySummary(result.summary); setOriginalSummary(result.summary);
      setIsTranslated(false); setAlreadySaved(false); setTab(0);
    } catch (err) {
      setError(err.message || 'Something went wrong while summarizing.');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (isGuest) { setError('Guest users can copy summaries, but cannot save them.'); return; }
    if (!data) return;
    setSaving(true);
    try {
      const summaryToSave = originalSummary || displaySummary;
      await api.saveSummary({
        title: summaryToSave.split(' ').slice(0, 4).join(' ') + '…',
        url: url || data.url, video_id: data.video_id, summary: summaryToSave,
        key_points: data.key_points, transcript_length: data.transcript_length,
        thumbnail_url: data.thumbnail_url || '',
      });
      setAlreadySaved(true); setSuccess('Summary saved successfully!'); setRefreshKey((k) => k + 1);
    } catch (err) {
      setError(err.message || 'Failed to save summary');
    } finally {
      setSaving(false);
    }
  };

  const handleTranslate = async () => {
    if (!originalSummary) { setError('No summary available to translate.'); return; }
    if (isTranslated) { setDisplaySummary(originalSummary); setIsTranslated(false); return; }
    setTranslating(true);
    try {
      const result = await api.translateSummary(originalSummary, lang);
      setDisplaySummary(result.translated_text); setIsTranslated(true);
    } catch (err) {
      setError(err.message || 'Translation failed');
    } finally {
      setTranslating(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(displaySummary);
    setSuccess('Copied to clipboard!');
  };

  const videoId = extractVideoId(url);
  const wordCount = displaySummary ? displaySummary.split(/\s+/).filter(Boolean).length : 0;

  return (
    <div style={{ minHeight: '100vh' }}>
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)}
        onSelect={handleSelectSummary} onNew={handleNewSummary} refreshKey={refreshKey} />

      <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 24px', height: 60, borderBottom: '1px solid var(--border)',
        position: 'sticky', top: 0, background: 'rgba(8,9,11,0.9)', backdropFilter: 'blur(20px)', zIndex: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button className="btn btn-ghost" onClick={() => setSidebarOpen(true)}>☰</button>
          <strong style={{ fontFamily: 'var(--ff-head)' }}>Snap<span style={{ color: 'var(--accent)' }}>Summ</span></strong>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 13, color: 'var(--text2)' }}>{isGuest ? 'Guest' : user?.username}</span>
          {user?.is_admin && <Link className="btn btn-ghost" to="/admin">Admin</Link>}
          <button className="btn btn-ghost" onClick={logout}>Logout</button>
        </div>
      </header>

      <main style={{ maxWidth: 720, margin: '0 auto', padding: '40px 20px 100px' }}>
        <h1 style={{ fontFamily: 'var(--ff-head)', fontSize: 32, fontWeight: 800, marginBottom: 8 }}>
          Turn hours into <em style={{ color: 'var(--accent)' }}>minutes.</em>
        </h1>
        <p style={{ color: 'var(--text2)', marginBottom: 28 }}>
          Paste any YouTube URL and get a clean, accurate summary with key points.
        </p>

        <form onSubmit={handleSummarize} style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
          <input ref={urlInputRef} value={url} onChange={(e) => setUrl(e.target.value)}
            placeholder="https://youtube.com/watch?v=..."
            style={{ flex: 1, padding: '12px 14px', background: 'var(--surface2)',
              border: '1px solid var(--border2)', borderRadius: 8, color: 'var(--text)',
              fontFamily: 'var(--ff-mono)', fontSize: 13 }} />
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? 'Summarizing…' : 'Summarize →'}
          </button>
        </form>

        {videoId && (
          <img src={`https://img.youtube.com/vi/${videoId}/hqdefault.jpg`} alt="Video thumbnail"
            style={{ width: '100%', borderRadius: 8, marginBottom: 20 }} />
        )}

        {error && <div className="error-banner">{error}</div>}
        {success && <div className="success-banner">{success}</div>}

        {loading && (
          <div className="card" style={{ textAlign: 'center', color: 'var(--text2)' }}>
            Fetching captions, chunking transcript, running AI summarization, extracting key points…
          </div>
        )}

        {data && !loading && (
          <div className="card">
            <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 12, color: 'var(--accent)', border: '1px solid var(--border2)', borderRadius: 20, padding: '4px 10px' }}>
                ID: {data.video_id}
              </span>
              <span style={{ fontSize: 12, color: 'var(--text2)', border: '1px solid var(--border2)', borderRadius: 20, padding: '4px 10px' }}>
                {data.transcript_length?.toLocaleString?.() ?? data.transcript_length} words transcribed
              </span>
              <span style={{ fontSize: 12, color: 'var(--text2)', border: '1px solid var(--border2)', borderRadius: 20, padding: '4px 10px' }}>
                {data.key_points?.length ?? 0} key points
              </span>
            </div>

            <div style={{ display: 'flex', gap: 16, borderBottom: '1px solid var(--border)', marginBottom: 16 }}>
              {['Summary', 'Key Points', 'Raw Info'].map((label, i) => (
                <div key={label} onClick={() => setTab(i)}
                  style={{ padding: '8px 0', cursor: 'pointer', fontSize: 13, fontWeight: 600,
                    color: tab === i ? 'var(--accent)' : 'var(--text2)',
                    borderBottom: tab === i ? '2px solid var(--accent)' : '2px solid transparent' }}>
                  {label}
                </div>
              ))}
            </div>

            {tab === 0 && (
              <>
                <div style={{ fontSize: 12, color: 'var(--text2)', marginBottom: 10 }}>{wordCount} words</div>
                <p style={{ lineHeight: 1.7, marginBottom: 20, whiteSpace: 'pre-wrap' }}>{displaySummary}</p>
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                  <select value={lang} onChange={(e) => setLang(e.target.value)} disabled={translating}>
                    {Object.entries(LANGUAGES).map(([code, name]) => <option key={code} value={code}>{name}</option>)}
                  </select>
                  <button className="btn btn-ghost" onClick={handleTranslate} disabled={translating}>
                    {translating ? 'Translating…' : isTranslated ? 'Show English' : 'Translate'}
                  </button>
                  <button className="btn btn-ghost" onClick={handleCopy}>Copy</button>
                  <button className="btn btn-primary" onClick={handleSave} disabled={saving || alreadySaved}>
                    {alreadySaved ? '✓ Saved' : saving ? 'Saving…' : 'Save'}
                  </button>
                </div>
              </>
            )}

            {tab === 1 && (
              <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 10 }}>
                {(data.key_points || []).map((p, i) => (
                  <li key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                    <span style={{ width: 22, height: 22, borderRadius: 4, background: 'var(--accent-dim)',
                      border: '1px solid rgba(240,118,69,0.2)', display: 'flex', alignItems: 'center',
                      justifyContent: 'center', fontSize: 10, color: 'var(--accent)', flexShrink: 0 }}>
                      {String(i + 1).padStart(2, '0')}
                    </span>
                    <span>{p}</span>
                  </li>
                ))}
              </ul>
            )}

            {tab === 2 && (
              <pre style={{ fontFamily: 'var(--ff-mono)', fontSize: 12, color: 'var(--text2)', lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>
{`Video ID        : ${data.video_id}
Transcript words: ${data.transcript_length}
Summary words   : ${wordCount}
Key points      : ${data.key_points?.length ?? 0}
URL             : ${data.url || url}`}
              </pre>
            )}
          </div>
        )}
      </main>
    </div>
  );
}