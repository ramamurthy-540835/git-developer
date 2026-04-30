'use client';
import { useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import MetricsCard from './MetricsCard';
import PublishButtons from './PublishButtons';

export default function ReadmeOutput({ readme, setReadme, metrics, setToast, onPrOpen, gitOps, repoUrl, runErrors, onMergePr, onClosePr }) {
  const [edit, setEdit] = useState(false);
  const readingMins = useMemo(() => Math.max(1, Math.ceil((readme || '').split(/\s+/).filter(Boolean).length / 220)), [readme]);
  const download = () => { const b = new Blob([readme || ''], { type:'text/markdown' }); const u = URL.createObjectURL(b); const a = document.createElement('a'); a.href = u; a.download = 'README.generated.md'; a.click(); URL.revokeObjectURL(u); };
  const copy = async () => { await navigator.clipboard.writeText(readme || ''); setToast('Copied to clipboard!'); };

  return <section className='split'><div className='card grid'>
    <div style={{ display:'flex', justifyContent:'space-between' }}><h3>README Output</h3><button className='btn' onClick={()=>setEdit(!edit)} aria-label='Toggle edit mode'>✏️ Edit</button></div>
    {edit ? <textarea className='textarea' value={readme} onChange={(e)=>setReadme(e.target.value)} /> : (
      <div style={{ lineHeight: 1.6 }}>
        <ReactMarkdown
          components={{
            code(props) {
              const { children, className, ...rest } = props;
              const match = /language-(\w+)/.exec(className || '');
              return match ? <SyntaxHighlighter {...rest} style={oneDark} language={match[1]} PreTag='div'>{String(children).replace(/\n$/, '')}</SyntaxHighlighter> : <code className={className} {...rest}>{children}</code>;
            },
          }}
        >{readme || 'README preview will appear here.'}</ReactMarkdown>
      </div>
    )}
    <PublishButtons onDownload={download} onCopy={copy} onPr={onPrOpen} />
  </div><MetricsCard metrics={metrics} readingMins={readingMins} gitOps={gitOps} runErrors={runErrors} readme={readme} repoUrl={repoUrl} onMergePr={onMergePr} onClosePr={onClosePr} /></section>;
}
