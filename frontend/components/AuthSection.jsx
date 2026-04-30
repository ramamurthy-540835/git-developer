'use client';
import { useState } from 'react';
import ErrorBanner from './ErrorBanner';
import { useAppStore } from '../store/useAppStore';
import { fetchRepos } from '../lib/api';

export default function AuthSection() {
  const { token, setToken, user, setUser, setRepos } = useAppStore();
  const [show, setShow] = useState(false);
  const [error, setError] = useState('');

  const connect = async () => {
    try {
      setError('');
      const data = await fetchRepos(token);
      const repos = Array.isArray(data) ? data : data.repos || [];
      setRepos(repos);
      setUser({ login: data.user?.login || 'connected-user', avatar_url: data.user?.avatar_url || '' });
    } catch (e) {
      setError(e.message || 'Invalid token: Token expired or has insufficient permissions. Get a new one.');
    }
  };

  return <section className='card grid'>
    <h3>Connect GitHub</h3>
    <ErrorBanner message={error} onDismiss={() => setError('')} />
    <label htmlFor='gh-token'>Token</label>
    <div style={{ display:'flex', gap:8 }}>
      <input id='gh-token' className='input' type={show ? 'text' : 'password'} value={token} onChange={(e)=>setToken(e.target.value)} aria-label='GitHub token' />
      <button className='btn' onClick={()=>setShow(!show)}>{show?'Hide':'Show'}</button>
    </div>
    <div>{user ? 'Connected ✓' : 'Disconnected ✗'}</div>
    {!user ? <button className='btn btn-primary' onClick={connect}>Connect</button> : <button className='btn' onClick={()=>{ setUser(null); setRepos([]); }}>Disconnect</button>}
  </section>;
}
