'use client';
import { useState } from 'react';
import { post } from '../lib/api';
import { useAppStore } from '../store/useAppStore';

export default function GenerationForm({ onJob }) {
  const token = useAppStore((s) => s.token);
  const selectedRepo = useAppStore((s) => s.selectedRepo);
  const settings = useAppStore((s) => s.settings);
  const setSettings = useAppStore((s) => s.setSettings);
  const [loading, setLoading] = useState(false);

  const generate = async () => {
    if (!selectedRepo?.url) return;
    setLoading(true);
    try {
      const d = await post('/api/generate-readme', { repo_url: selectedRepo.url, github_token: token });
      onJob(d.job_id);
    } catch (e) { alert(e.message); }
    finally { setLoading(false); }
  };

  return <section className='panel' style={{ padding: 16 }}>
    <h3>Generation Options</h3>
    <div style={{ display: 'grid', gap: 8 }}>
      <input className='input' value={selectedRepo?.url || ''} readOnly placeholder='Select repository first' />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        <select className='select' value={settings.length} onChange={(e) => setSettings({ length: e.target.value })}><option>Short</option><option>Medium</option><option>Detailed</option></select>
        <select className='select' value={settings.style} onChange={(e) => setSettings({ style: e.target.value })}><option>Technical</option><option>Executive</option><option>Tutorial</option></select>
      </div>
      <label>Tone: {settings.tone}</label>
      <input type='range' min='0' max='100' value={settings.tone} onChange={(e) => setSettings({ tone: Number(e.target.value) })} />
      <button className='btn btn-primary' onClick={generate} disabled={!token || !selectedRepo || loading}>{loading ? 'Starting...' : 'Generate README (~30s)'}</button>
    </div>
  </section>;
}
