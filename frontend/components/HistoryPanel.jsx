'use client';
import { useAppStore } from '../store/useAppStore';
export default function HistoryPanel() { const history = useAppStore((s)=>s.history); return <section className='card grid'><h3>History</h3>{history.map((h,i)=><div key={i} className='progress-item'><span>{new Date(h.ts).toLocaleString()} · {h.repo}</span><span>Score {h.score}</span></div>)}</section>; }
