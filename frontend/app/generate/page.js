'use client';
import { useState } from 'react';
import AuthSection from '../../components/AuthSection';
import RepoSelector from '../../components/RepoSelector';
import GenerationOptions from '../../components/GenerationOptions';
import ProgressStream from '../../components/ProgressStream';
import ReadmeOutput from '../../components/ReadmeOutput';
import ToastNotification from '../../components/ToastNotification';
import CreatePrModal from '../../components/CreatePrModal';
import { useAppStore } from '../../store/useAppStore';
import { generateReadme, pollJob, publishReadme } from '../../lib/api';

export default function GeneratePage() {
  const { selectedRepo, token, addHistory } = useAppStore();
  const [generating, setGenerating] = useState(false);
  const [toast, setToast] = useState('');
  const [toastTone, setToastTone] = useState('success');
  const [readme, setReadme] = useState('');
  const [metrics, setMetrics] = useState(null);
  const [stages, setStages] = useState([]);
  const [statusText, setStatusText] = useState('Waiting to start');
  const [prOpen, setPrOpen] = useState(false);

  const onGenerate = async (options) => {
    if (!selectedRepo?.url || !token) {
      setToastTone('error');
      setToast('Error generating README. Check repo access.');
      return;
    }
    setGenerating(true);
    setStages([{ name:'Analyzing repository', state:'active' }, { name:'Finding competitors', state:'pending' }, { name:'Extracting best practices', state:'pending' }, { name:'Composing README', state:'pending' }]);
    try {
      const started = await generateReadme({ repoUrl: selectedRepo.url, githubToken: token, options });
      const jobId = started.job_id;
      let done = false;
      while (!done) {
        // eslint-disable-next-line no-await-in-loop
        const j = await pollJob(jobId);
        const s = j?.status || '';
        setStatusText(j?.message || 'Scanning requirements.txt');
        if (s === 'completed') {
          const result = j.result || {};
          setReadme(result.readme_markdown || '');
          setMetrics(result.metrics || null);
          if (result.metrics) addHistory({ repo: selectedRepo.full_name || selectedRepo.url, score: result.metrics.quality_score || 0, ts: Date.now() });
          setStages((prev) => prev.map((x) => ({ ...x, state:'done', time: '2s ago' })));
          setToastTone('success');
          setToast('README generated successfully');
          done = true;
        } else if (s === 'failed') {
          throw new Error(j?.error || 'Generation failed');
        } else {
          setStages((prev) => {
            const idx = Math.min(3, Math.floor((Date.now() / 1500) % 4));
            return prev.map((x, i) => ({ ...x, state: i < idx ? 'done' : i === idx ? 'active' : 'pending' }));
          });
          // eslint-disable-next-line no-await-in-loop
          await new Promise((r) => setTimeout(r, 1000));
        }
      }
    } catch (e) {
      setToastTone('error');
      setToast(e.message || 'Error generating README. Check repo access.');
    } finally {
      setGenerating(false);
    }
  };

  const onPrSubmit = async ({ branch, commitMessage, prTitle, prBody }) => {
    const d = await publishReadme({ repoUrl: selectedRepo.url, readmeMarkdown: readme, githubToken: token, branch, commitMessage, prTitle, prBody });
    setToastTone('success');
    setToast(d.pr_url ? `PR created successfully! View PR #${d.pr_number}` : 'PR created successfully!');
  };

  return <div className='grid'>
    <section className='hero'><h1 style={{ marginTop:0 }}>Generate professional READMEs in seconds</h1><p style={{ color:'var(--color-text-muted)' }}>AI-powered. Competitive analysis included.</p></section>
    <AuthSection />
    <RepoSelector />
    <GenerationOptions onGenerate={onGenerate} generating={generating} />
    {generating && <ProgressStream stages={stages} statusText={statusText} eta='~8 seconds' onAbort={() => setGenerating(false)} />}
    <ReadmeOutput readme={readme} setReadme={setReadme} metrics={metrics} setToast={setToast} onPrOpen={() => setPrOpen(true)} />
    <CreatePrModal open={prOpen} onClose={() => setPrOpen(false)} onSubmit={onPrSubmit} repoName={selectedRepo?.full_name || ''} />
    <ToastNotification message={toast} tone={toastTone} onDone={() => setToast('')} />
  </div>;
}
