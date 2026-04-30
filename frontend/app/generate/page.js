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
import { closePr, generateReadme, mergePr, pollJob, publishReadme } from '../../lib/api';

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
  const [gitOps, setGitOps] = useState(null);
  const [runErrors, setRunErrors] = useState([]);
  const diag = {
    llm: metrics?.used_llm ? 'Gemini 2.5 Flash' : 'Fallback',
    quality: metrics?.quality_score ?? 0,
    completeness: metrics?.completeness ?? 0,
    readTime: metrics?.estimated_read_time_min ?? 0,
  };

  const onGenerate = async (options) => {
    if (!selectedRepo?.url || !token) {
      setToastTone('error');
      setToast('Error generating README. Check repo access.');
      return;
    }
    setGenerating(true);
    setRunErrors([]);
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
          setRunErrors(result.errors || []);
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
    setGitOps({
      branch: d.branch || branch,
      prNumber: d.pr_number || null,
      prUrl: d.pr_url || '',
      status: d.pr_already_exists ? 'Updated existing PR' : 'Created new PR',
      commitSha: d.commit_sha || '',
      commitUrl: d.commit_url || '',
      baseBranch: d.base_branch || '',
      headBranch: d.head_branch || '',
      validation: d.validation || null,
    });
    setToastTone('success');
    setToast(d.pr_already_exists ? `Existing PR updated: #${d.pr_number}` : (d.pr_url ? `PR created successfully! View PR #${d.pr_number}` : 'PR created successfully!'));
  };

  const onMergePr = async () => {
    if (!gitOps?.prNumber || !selectedRepo?.url || !token) return;
    const d = await mergePr({ repoUrl: selectedRepo.url, githubToken: token, prNumber: gitOps.prNumber, mergeMethod: 'squash' });
    setGitOps((prev) => ({ ...(prev || {}), status: 'Merged to main', mergeSha: d?.result?.sha || '' }));
    setToastTone('success');
    setToast(`PR #${gitOps.prNumber} merged successfully`);
  };

  const onClosePr = async () => {
    if (!gitOps?.prNumber || !selectedRepo?.url || !token) return;
    await closePr({ repoUrl: selectedRepo.url, githubToken: token, prNumber: gitOps.prNumber });
    setGitOps((prev) => ({ ...(prev || {}), status: 'Closed PR' }));
    setToastTone('success');
    setToast(`PR #${gitOps.prNumber} closed`);
  };

  return <div className='grid'>
    <section className='hero'><h1 style={{ marginTop:0 }}>Generate professional READMEs in seconds</h1><p style={{ color:'var(--color-text-muted)' }}>AI-powered. Competitive analysis included.</p></section>
    <section className='card diag-strip'>
      <div><strong>LLM Engine</strong><div>{diag.llm}</div></div>
      <div><strong>Quality</strong><div>{diag.quality}</div></div>
      <div><strong>Completeness</strong><div>{diag.completeness}%</div></div>
      <div><strong>Read Time</strong><div>{diag.readTime} min</div></div>
    </section>
    <AuthSection />
    <RepoSelector />
    <GenerationOptions onGenerate={onGenerate} generating={generating} />
    {generating && <ProgressStream stages={stages} statusText={statusText} eta='~8 seconds' onAbort={() => setGenerating(false)} />}
    <ReadmeOutput readme={readme} setReadme={setReadme} metrics={metrics} gitOps={gitOps} runErrors={runErrors} repoUrl={selectedRepo?.url || ''} setToast={setToast} onPrOpen={() => setPrOpen(true)} onMergePr={onMergePr} onClosePr={onClosePr} />
    <CreatePrModal open={prOpen} onClose={() => setPrOpen(false)} onSubmit={onPrSubmit} repoName={selectedRepo?.full_name || ''} />
    <ToastNotification message={toast} tone={toastTone} onDone={() => setToast('')} />
  </div>;
}
