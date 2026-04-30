'use client';

import { useMemo, useState } from 'react';
import ProgressStream from '../../components/ProgressStream';

export default function GeneratePage() {
  const apiBaseUrl = useMemo(() => {
    return process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
  }, []);

  const [githubToken, setGithubToken] = useState('');
  const [repoUrl, setRepoUrl] = useState('https://github.com/ramamurthy-540835/git-developer');
  const [jobId, setJobId] = useState('');
  const [loading, setLoading] = useState(false);
  const [readme, setReadme] = useState('');
  const [metrics, setMetrics] = useState(null);
  const [status, setStatus] = useState('');
  const [branch, setBranch] = useState('main');
  const [commitMessage, setCommitMessage] = useState('docs: update generated README');

  const startGeneration = async () => {
    setLoading(true);
    setStatus('Starting generation...');
    setReadme('');
    setMetrics(null);
    try {
      const res = await fetch(`${apiBaseUrl}/api/generate-readme`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_url: repoUrl, github_token: githubToken }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to start generation');
      setJobId(data.job_id);
      setStatus(`Job started: ${data.job_id}`);
    } catch (e) {
      setStatus(`Error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const publishReadme = async () => {
    setStatus('Publishing README...');
    try {
      const res = await fetch(`${apiBaseUrl}/api/publish-readme`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_url: repoUrl,
          readme_markdown: readme,
          github_token: githubToken,
          branch,
          commit_message: commitMessage,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Publish failed');
      setStatus(`Published to ${data.result.repo} on ${data.result.branch}`);
    } catch (e) {
      setStatus(`Publish error: ${e.message}`);
    }
  };

  return (
    <main style={{ maxWidth: 1100, margin: '24px auto', padding: '0 16px', fontFamily: 'ui-sans-serif, system-ui' }}>
      <h1 style={{ fontSize: 28, marginBottom: 16 }}>README Generator</h1>

      <div style={{ display: 'grid', gap: 12, marginBottom: 16 }}>
        <input
          type='password'
          placeholder='GitHub Token'
          value={githubToken}
          onChange={(e) => setGithubToken(e.target.value)}
          style={{ padding: 10, border: '1px solid #ccc', borderRadius: 8 }}
        />
        <input
          type='text'
          placeholder='Repository URL'
          value={repoUrl}
          onChange={(e) => setRepoUrl(e.target.value)}
          style={{ padding: 10, border: '1px solid #ccc', borderRadius: 8 }}
        />
        <button onClick={startGeneration} disabled={loading || !githubToken || !repoUrl} style={{ padding: '10px 14px', borderRadius: 8 }}>
          {loading ? 'Starting...' : 'Generate README'}
        </button>
      </div>

      {!!jobId && (
        <div style={{ marginBottom: 16 }}>
          <ProgressStream
            apiBaseUrl={apiBaseUrl}
            jobId={jobId}
            onFinal={(payload) => {
              const result = payload?.result || {};
              if (result.readme_markdown) setReadme(result.readme_markdown);
              if (result.metrics) setMetrics(result.metrics);
              setStatus(payload.status === 'completed' ? 'Generation completed' : `Generation failed: ${payload.error || 'unknown'}`);
            }}
          />
        </div>
      )}

      <div style={{ marginBottom: 12, color: '#374151' }}>{status}</div>

      {metrics && (
        <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
          <Metric label='Quality Score' value={metrics.quality_score} />
          <Metric label='Completeness' value={`${metrics.completeness}%`} />
          <Metric label='Uniqueness' value={`${metrics.uniqueness_score}%`} />
          <Metric label='Read Time' value={`${metrics.estimated_read_time_min} min`} />
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 12 }}>
        <textarea
          value={readme}
          onChange={(e) => setReadme(e.target.value)}
          placeholder='Generated README markdown will appear here...'
          style={{ width: '100%', minHeight: 420, padding: 12, borderRadius: 8, border: '1px solid #ccc', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' }}
        />
      </div>

      <div style={{ marginTop: 16, display: 'grid', gap: 8 }}>
        <h3>Publish</h3>
        <input value={branch} onChange={(e) => setBranch(e.target.value)} placeholder='Branch' style={{ padding: 10, border: '1px solid #ccc', borderRadius: 8 }} />
        <input value={commitMessage} onChange={(e) => setCommitMessage(e.target.value)} placeholder='Commit message' style={{ padding: 10, border: '1px solid #ccc', borderRadius: 8 }} />
        <button onClick={publishReadme} disabled={!readme || !githubToken || !repoUrl} style={{ padding: '10px 14px', borderRadius: 8 }}>
          Publish README
        </button>
      </div>
    </main>
  );
}

function Metric({ label, value }) {
  return (
    <div style={{ border: '1px solid #ddd', borderRadius: 8, padding: 12, minWidth: 160 }}>
      <div style={{ fontSize: 12, color: '#6b7280' }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700 }}>{value}</div>
    </div>
  );
}
