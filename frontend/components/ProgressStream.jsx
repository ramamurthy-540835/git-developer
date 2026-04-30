export default function ProgressStream({ stages, statusText, eta, onAbort }) {
  return <section className='card grid'><div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}><h3>Generation Progress</h3><button className='btn btn-danger' onClick={onAbort}>Abort</button></div>
    {stages.map((s)=><div key={s.name} className='progress-item'><span>{s.state==='done'?'✓':s.state==='active'?'⟳':'○'} {s.name}</span><span>{s.state==='done' ? (s.time || '2s ago') : s.state==='active' ? 'in progress' : 'pending'}</span></div>)}
    <div>{statusText}<span className='ellipsis'>...</span></div><div style={{ color:'var(--color-text-muted)' }}>Estimated time remaining: {eta}</div>
  </section>;
}
