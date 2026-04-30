'use client';

import { useMemo, useState } from 'react';
import { useAppStore } from '../store/useAppStore';

function langColor(language) {
  const map = {
    JavaScript: '#f1e05a',
    TypeScript: '#3178c6',
    Python: '#3572A5',
    Java: '#b07219',
    Go: '#00ADD8',
    Rust: '#dea584',
  };
  return map[language] || '#8b949e';
}

export default function RepoSelector() {
  const { repos, selectedRepo, setSelectedRepo } = useAppStore();
  const [query, setQuery] = useState('');

  const filteredRepos = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return repos;
    return repos.filter((r) =>
      [r.full_name, r.name, r.description].filter(Boolean).join(' ').toLowerCase().includes(q)
    );
  }, [repos, query]);

  return (
    <section className='card grid' aria-labelledby='repo-selector-title'>
      <h3 id='repo-selector-title'>Select Repository</h3>

      <label htmlFor='repo-search'>
        Search repositories <span style={{ color: 'var(--color-text-muted)' }}>(Required)</span>
      </label>
      <input
        id='repo-search'
        className='input'
        aria-label='Search repositories'
        placeholder={`Search your ${repos.length} public repos...`}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={(e) => {
          e.currentTarget.setAttribute('data-prev-placeholder', e.currentTarget.placeholder);
          e.currentTarget.placeholder = '';
        }}
        onBlur={(e) => {
          if (!e.currentTarget.placeholder) {
            e.currentTarget.placeholder = e.currentTarget.getAttribute('data-prev-placeholder') || '';
          }
        }}
        onKeyDown={(e) => {
          if (e.key === 'Escape') setQuery('');
        }}
      />

      {filteredRepos.length === 0 ? (
        <div role='status' aria-live='polite'>No repos found</div>
      ) : (
        <div className='repo-grid' role='listbox' aria-label='Repository list'>
          {filteredRepos.map((repo) => {
            const selected = selectedRepo?.id === repo.id;
            return (
              <button
                key={repo.id || repo.full_name}
                type='button'
                role='option'
                aria-selected={selected}
                aria-label={`Select repository ${repo.full_name || repo.name}`}
                className={`repo-card ${selected ? 'selected' : ''}`}
                onClick={() => setSelectedRepo(repo)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span
                      aria-hidden
                      style={{
                        width: 10,
                        height: 10,
                        borderRadius: 999,
                        background: langColor(repo.language),
                        display: 'inline-block',
                      }}
                    />
                    <strong>{repo.full_name || repo.name}</strong>
                  </div>
                  <span aria-hidden>{selected ? '✓' : '○'}</span>
                </div>

                <p style={{ color: 'var(--color-text-muted)', margin: '8px 0 0' }}>
                  {repo.description || 'No description'}
                </p>

                <div style={{ marginTop: 10, color: 'var(--color-text-muted)', fontSize: 13 }}>
                  ⭐ {repo.stargazers_count || 0}
                  {repo.language ? ` · ${repo.language}` : ''}
                </div>
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
}
