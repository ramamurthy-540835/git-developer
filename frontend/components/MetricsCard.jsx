function parseReadmeChanges(readme = '') {
  const headings = (readme.match(/^##\s+.+$/gm) || []).map((h) => h.replace(/^##\s+/, '').trim());
  return {
    sections: headings.slice(0, 10),
    sectionCount: headings.length,
    mermaidCount: (readme.match(/```mermaid/g) || []).length,
    hasApiRef: /##\s+API Reference/i.test(readme),
    hasArchitecture: /##\s+Architecture/i.test(readme),
  };
}

function statusTone(status = '') {
  if (/Created|Updated/.test(status)) return 'var(--color-success)';
  if (/Not published/.test(status)) return 'var(--color-warning)';
  return 'var(--color-text-muted)';
}

export default function MetricsCard({ metrics, readingMins, gitOps, readme, repoUrl, runErrors, onMergePr, onClosePr }) {
  const score = metrics?.quality_score || 0;
  const color = score >= 80 ? 'var(--color-success)' : score >= 60 ? 'var(--color-warning)' : 'var(--color-error)';
  const completeness = metrics?.completeness || 0;
  const change = parseReadmeChanges(readme);
  return <aside className='card grid'>
    <h4>Metrics</h4>
    <div style={{ display:'flex', justifyContent:'center' }}>
      <svg width='140' height='90' viewBox='0 0 140 90' aria-label='Quality score gauge'>
        <path d='M10 80 A60 60 0 0 1 130 80' fill='none' stroke='var(--color-border)' strokeWidth='12' />
        <path d='M10 80 A60 60 0 0 1 130 80' fill='none' stroke={color} strokeWidth='12' strokeDasharray={`${(score/100)*188} 188`} />
        <text x='70' y='72' textAnchor='middle' style={{ fill:'var(--color-text)', fontWeight:700 }}>{score}</text>
      </svg>
    </div>
    <div>Completeness: {completeness}%</div>
    <progress max='100' value={completeness} aria-label='Completeness progress' />
    <div>Estimated reading time: {readingMins} min</div>
    <hr style={{ borderColor: 'var(--color-border)', width: '100%' }} />
    <h4 style={{ margin: 0 }}>Git Operations</h4>
    <div className='ops-flow'>
      <span className='op-node done'>Generate</span>
      <span className='op-arrow'>→</span>
      <span className='op-node done'>Commit</span>
      <span className='op-arrow'>→</span>
      <span className='op-node done'>Push</span>
      <span className='op-arrow'>→</span>
      <span className='op-node active'>PR</span>
      <span className='op-arrow'>→</span>
      <span className='op-node'>Merge</span>
    </div>
    <div>Branch: {gitOps?.branch || '-'}</div>
    <div>Base/Head: {gitOps?.baseBranch ? `${gitOps.baseBranch} ← ${gitOps.headBranch}` : '-'}</div>
    <div>Status: <span style={{ color: statusTone(gitOps?.status) }}>{gitOps?.status || 'Not published'}</span></div>
    <div>PR: {gitOps?.prNumber ? `#${gitOps.prNumber}` : '-'}</div>
    {gitOps?.prUrl ? <a href={gitOps.prUrl} target='_blank' rel='noreferrer'>Open PR</a> : null}
    {gitOps?.prNumber ? <div className='ops-actions'>
      <button className='btn btn-compact btn-primary' onClick={onMergePr}>Merge PR</button>
      <button className='btn btn-compact' onClick={onClosePr}>Close PR</button>
    </div> : null}
    <div>Commit: {gitOps?.commitSha ? gitOps.commitSha.slice(0, 7) : '-'}</div>
    {gitOps?.commitUrl ? <a href={gitOps.commitUrl} target='_blank' rel='noreferrer'>Open Commit</a> : null}
    {repoUrl ? <a href={repoUrl} target='_blank' rel='noreferrer'>Open Repository</a> : null}
    <div>Validation: {gitOps?.validation?.valid ? (gitOps.validation.repaired ? 'Passed (auto-repaired)' : 'Passed') : 'Unknown'}</div>
    <hr style={{ borderColor: 'var(--color-border)', width: '100%' }} />
    <h4 style={{ margin: 0 }}>Actual Changes</h4>
    <div>Sections detected: {change.sectionCount}</div>
    <div>Mermaid diagrams: {change.mermaidCount}</div>
    <div>Architecture section: {change.hasArchitecture ? 'Yes' : 'No'}</div>
    <div>API Reference section: {change.hasApiRef ? 'Yes' : 'No'}</div>
    <div style={{ color: 'var(--color-text-muted)', fontSize: 12 }}>Top sections:</div>
    <div style={{ fontSize: 12 }}>
      {change.sections.length ? change.sections.map((s) => <div key={s}>• {s}</div>) : <div>• None detected</div>}
    </div>
    <hr style={{ borderColor: 'var(--color-border)', width: '100%' }} />
    <h4 style={{ margin: 0 }}>LangGraph Diagnostics</h4>
    <div style={{ fontSize: 12 }}>
      {runErrors?.length ? runErrors.map((e, i) => <div key={`${i}-${e}`}>• {e}</div>) : <div>• No workflow errors reported</div>}
    </div>
  </aside>;
}
