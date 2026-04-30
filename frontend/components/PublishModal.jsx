'use client';
import { useState } from 'react';
import { publishReadme } from '../lib/api';
import { useAppStore } from '../store/useAppStore';
import ErrorBanner from './ErrorBanner';

export default function PublishModal({ readme }) {
  const token = useAppStore((s) => s.token);
  const selectedRepo = useAppStore((s) => s.selectedRepo);
  const [branch, setBranch] = useState('docs/update-readme');
  const [message, setMessage] = useState('docs: update generated README');
  const [prTitle, setPrTitle] = useState('docs: update README');
  const [prBody, setPrBody] = useState('Auto-generated README by git-developer');
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const publish = async () => {
    if (!prTitle.trim() || prTitle.length > 100) return setError('PR title is required (max 100 chars).');
    if (prBody.length > 5000) return setError('PR body max length is 5000 chars.');
    try {
      setError('');
      setLoading(true);
      const d = await publishReadme({ repoUrl: selectedRepo.url, readmeMarkdown: readme, githubToken: token, branch, commitMessage: message, prTitle, prBody });
      setResult({ url: d.pr_url, number: d.pr_number, title: d.pr_title });
    } catch (e) {
      setError(e.message || 'Publish failed');
    } finally {
      setLoading(false);
    }
  };

  if (!readme) return null;
  return <section className='card grid'>
    <h3>Publish Options</h3>
    <ErrorBanner message={error} onDismiss={() => setError('')} />
    <div style={{ display: 'grid', gap: 8 }}>
      <input className='input' value={branch} onChange={(e) => setBranch(e.target.value)} aria-label='Branch' />
      <input className='input' value={message} onChange={(e) => setMessage(e.target.value)} aria-label='Commit message' />
      <label htmlFor='pr-title-inline'>PR Title (Required)</label>
      <input id='pr-title-inline' className='input' value={prTitle} onChange={(e) => setPrTitle(e.target.value.slice(0, 100))} aria-label='PR title' />
      <div style={{ color: 'var(--color-text-muted)', fontSize: 12 }}>{prTitle.length}/100</div>
      <label htmlFor='pr-body-inline'>PR Body</label>
      <textarea id='pr-body-inline' className='textarea' value={prBody} onChange={(e) => setPrBody(e.target.value.slice(0, 5000))} aria-label='PR body' />
      <div style={{ color: 'var(--color-text-muted)', fontSize: 12 }}>{prBody.length}/5000</div>
      <button className='btn btn-primary' onClick={publish} disabled={!token || !selectedRepo || !prTitle.trim() || loading}>{loading ? <><span className='spinner' />Loading...</> : 'Create GitHub PR'}</button>
      {result?.url ? <div><strong>PR created successfully!</strong> <a href={result.url} target='_blank' rel='noreferrer'>View PR #{result.number}</a></div> : null}
    </div>
  </section>;
}
