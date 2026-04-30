'use client';
import { useEffect, useRef, useState } from 'react';
import ErrorBanner from './ErrorBanner';

export default function CreatePrModal({ open, onClose, onSubmit, defaultBranch = 'docs/update-readme', defaultMessage = 'docs: update generated README', repoName = '' }) {
  const [branch, setBranch] = useState(defaultBranch);
  const [commitMessage, setCommitMessage] = useState(defaultMessage);
  const [title, setTitle] = useState('docs: update README');
  const [body, setBody] = useState('Auto-generated README by git-developer');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const firstInputRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    setTimeout(() => firstInputRef.current?.focus(), 0);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  const submit = async (e) => {
    e.preventDefault();
    if (!branch.trim() || !commitMessage.trim() || !title.trim()) return setError('Branch, commit message, and PR title are required.');
    if (title.length > 100) return setError('PR title must be 100 characters or fewer.');
    if (body.length > 5000) return setError('PR body must be 5000 characters or fewer.');
    try {
      setError('');
      setLoading(true);
      await onSubmit({ branch: branch.trim(), commitMessage: commitMessage.trim(), prTitle: title.trim(), prBody: body.trim() });
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to create PR.');
    } finally {
      setLoading(false);
    }
  };

  return <div className='modal-backdrop' onClick={onClose} role='presentation'>
    <div className='modal-card' role='dialog' aria-modal='true' aria-label='Create pull request' onClick={(e) => e.stopPropagation()}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3>Create PR {repoName ? `for ${repoName}` : ''}</h3>
        <button className='btn' aria-label='Close PR modal' onClick={onClose}>✕</button>
      </div>
      <ErrorBanner message={error} onDismiss={() => setError('')} />
      <form className='grid' onSubmit={submit}>
        <label htmlFor='pr-branch'>Branch (Required)</label>
        <input id='pr-branch' ref={firstInputRef} className='input' value={branch} onChange={(e) => setBranch(e.target.value)} />
        <label htmlFor='pr-commit'>Commit Message (Required)</label>
        <input id='pr-commit' className='input' value={commitMessage} onChange={(e) => setCommitMessage(e.target.value)} />
        <label htmlFor='pr-title'>PR Title (Required)</label>
        <input id='pr-title' className='input' value={title} onChange={(e) => setTitle(e.target.value.slice(0, 100))} />
        <div style={{ color: 'var(--color-text-muted)', fontSize: 12 }}>{title.length}/100</div>
        <label htmlFor='pr-body'>PR Body</label>
        <textarea id='pr-body' className='textarea' value={body} onChange={(e) => setBody(e.target.value.slice(0, 5000))} maxLength={5000} />
        <div style={{ color: 'var(--color-text-muted)', fontSize: 12 }}>{body.length}/5000</div>
        <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
          <button type='button' className='btn' onClick={onClose}>Cancel</button>
          <button type='submit' className='btn btn-primary' disabled={loading || !title.trim()}>{loading ? <><span className='spinner' />Loading...</> : 'Create PR'}</button>
        </div>
      </form>
    </div>
  </div>;
}
