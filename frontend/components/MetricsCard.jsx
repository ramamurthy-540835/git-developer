export default function MetricsCard({ metrics, readingMins }) {
  const score = metrics?.quality_score || 0;
  const color = score >= 80 ? 'var(--color-success)' : score >= 60 ? 'var(--color-warning)' : 'var(--color-error)';
  const completeness = metrics?.completeness || 0;
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
  </aside>;
}
