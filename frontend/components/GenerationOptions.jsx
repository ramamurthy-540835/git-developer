'use client';
import { useState } from 'react';

export default function GenerationOptions({ onGenerate, generating }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ length:'Medium', style:'Technical', tone:50, sections:{ features:true, architecture:true, bestPractices:true, competitive:true } });
  return <section className='card grid'><button className='btn btn-secondary' onClick={()=>setOpen(!open)} aria-expanded={open}>Customize README {open ? '▲' : '▼'}</button>
    {open && <div className='grid'>
      <div>README Length: {['Short','Medium','Detailed'].map((v)=><label key={v} style={{marginRight:12}}><input type='radio' name='length' checked={form.length===v} onChange={()=>setForm({...form,length:v})} /> {v}</label>)}</div>
      <div>Style: {['Technical','Executive','Tutorial'].map((v)=><label key={v} style={{marginRight:12}}><input type='radio' name='style' checked={form.style===v} onChange={()=>setForm({...form,style:v})} /> {v}</label>)}</div>
      <div>Tone: <input type='range' min='0' max='100' value={form.tone} onChange={(e)=>setForm({...form,tone:+e.target.value})} /></div>
    </div>}
    <button className='btn btn-primary' onClick={()=>onGenerate(form)} disabled={generating}>{generating ? <><span className='spinner' />Loading...</> : 'Generate README'}</button>
  </section>;
}
