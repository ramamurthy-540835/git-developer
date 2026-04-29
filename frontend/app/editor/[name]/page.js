'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams, useSearchParams } from 'next/navigation'; // Import useSearchParams
import Link from 'next/link';

export default function EditorPage() {
  const params = useParams();
  const searchParams = useSearchParams(); // Get search params
  const rawNameParam = Array.isArray(params.name) ? params.name[0] : params.name;
  const fullRepoName = rawNameParam ? decodeURIComponent(rawNameParam) : ""; // owner/repo
  const repoUrl = searchParams.get('repo_url'); // Get repo_url from query params

  const [repoMetadata, setRepoMetadata] = useState(null);
  const [repoContext, setRepoContext] = useState(null); // This will hold the result of POST /api/repo-context
  const [transcript, setTranscript] = useState('');
  const [showSourceContext, setShowSourceContext] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [loadingRepoContext, setLoadingRepoContext] = useState(false);
  const [loadingTranscript, setLoadingTranscript] = useState(false);
  const [loadingMp3, setLoadingMp3] = useState(false);
  const [mp3Result, setMp3Result] = useState(null);
  const [mp3Status, setMp3Status] = useState('');
  const [videoJobId, setVideoJobId] = useState(null);
  const [videoJob, setVideoJob] = useState(null);
  const [loadingVideo, setLoadingVideo] = useState(false);
  const [rendererMode, setRendererMode] = useState('local_ffmpeg');
  const [videoPrompt, setVideoPrompt] = useState('');
  const [durationSeconds, setDurationSeconds] = useState(32);
  const [autoPromptMode, setAutoPromptMode] = useState(true);
  const [uploadToSharePoint, setUploadToSharePoint] = useState(true); // New state for SharePoint upload checkbox
  const statusText = {
    queued: 'Queued',
    generating_mp3: 'Generating audio',
    uploading_mp3: 'Uploading audio',
    rendering_video: 'Rendering video',
    uploading_video: 'Uploading video',
    completed: 'Completed',
    failed: 'Failed',
  };

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

  // Function to fetch repository metadata from config/repos.yaml
  const fetchRepoMetadata = useCallback(async () => {
    if (!fullRepoName) {
      setError("Repository name not provided in URL.");
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const response = await fetch(`${API_BASE_URL}/api/repos/${fullRepoName}`);
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Failed to fetch repository metadata! Status: ${response.status}`);
      }
      const data = await response.json();
      setRepoMetadata(data);
    } catch (e) {
      console.error("Error fetching repository metadata:", e);
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [fullRepoName]);

  // Function to fetch repository context (README, files, tech stack)
  const readRepoContext = useCallback(async () => {
    if (!repoUrl) {
      setError("Repository URL not provided.");
      return;
    }
    try {
      setLoadingRepoContext(true);
      setError(null);
      const response = await fetch(`${API_BASE_URL}/api/repo-context`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_url: repoUrl }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Failed to read repository context! Status: ${response.status}`);
      }
      const data = await response.json();
      setRepoContext(data);
    } catch (e) {
      console.error("Error reading repository context:", e);
      setError(e.message);
    } finally {
      setLoadingRepoContext(false);
    }
  }, [repoUrl]);

  // Function to generate transcript using repo context
  const generateTranscriptFromRepoContext = useCallback(async () => {
    if (!repoMetadata) {
      setError("Cannot generate transcript: Repository metadata not loaded.");
      return;
    }
    try {
      setLoadingTranscript(true);
      setError(null);
      setTranscript(''); // Clear previous transcript

      // Prepare app data from repoMetadata
      const appDataForTranscript = {
        name: repoMetadata.name,
        full_name: repoMetadata.full_name,
        repo_url: repoMetadata.repo_url,
        description: repoMetadata.description,
        language: repoMetadata.language,
        private: repoMetadata.private,
        updated_at: repoMetadata.updated_at,
        tags: repoMetadata.tags || [],
        url: repoMetadata.url, // Include original URL if it exists
      };

      const response = await fetch(`${API_BASE_URL}/api/transcript`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ app: appDataForTranscript }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Failed to generate transcript! Status: ${response.status}`);
      }

      const transcriptData = await response.json();
      setTranscript(transcriptData.transcript);
      if (transcriptData.warning) {
        setError(transcriptData.warning);
      }
    } catch (e) {
      console.error("Error generating transcript:", e);
      setError(e.message);
      setTranscript(`Failed to generate transcript: ${e.message}`);
    } finally {
      setLoadingTranscript(false);
    }
  }, [repoMetadata]);


  useEffect(() => {
    fetchRepoMetadata();
  }, [fetchRepoMetadata]);

  useEffect(() => {
    if (!autoPromptMode) return;
    const repoName = repoMetadata?.name || fullRepoName || 'this product';
    const desc = repoMetadata?.description || repoContext?.description || '';
    let flowHint = 'Show realistic workflow, key interactions, and business value.';
    if (durationSeconds <= 12) {
      flowHint = 'Focus on a fast hook and one core workflow moment with strong visual clarity.';
    } else if (durationSeconds <= 24) {
      flowHint = 'Cover hook, workflow demo, and business impact in a concise narrative.';
    } else if (durationSeconds <= 32) {
      flowHint = 'Use a 4-beat flow: problem, interaction workflow, AI insight, business outcome.';
    } else {
      flowHint = 'Use a full narrative flow with clear transitions across product value, workflow, AI insight, architecture, and outcomes.';
    }
    const autoPrompt = `Create a cinematic ${durationSeconds}-second product demo video for ${repoName}. `
      + `${flowHint} `
      + `Style: modern enterprise SaaS demo, smooth camera motion, readable UI overlays, clean composition. `
      + `Avoid clutter, generic stock scenes, and unreadable on-screen text. `
      + `Context: ${desc}. `
      + `Narration basis: ${transcript?.slice(0, 1000) || ''}`;
    setVideoPrompt(autoPrompt);
  }, [autoPromptMode, repoMetadata?.name, repoMetadata?.description, repoContext?.description, fullRepoName, durationSeconds, transcript]);

  // If repo metadata is loaded and repoUrl is available, attempt to read context automatically
  // useEffect(() => {
  //   if (repoMetadata && repoUrl && !repoContext && !loadingRepoContext) {
  //     readRepoContext();
  //   }
  // }, [repoMetadata, repoUrl, repoContext, loadingRepoContext, readRepoContext]);


  const handleGenerateMp3 = async () => {
    if (!transcript || !transcript.trim()) {
      setError("Transcript is empty. Generate transcript first.");
      return;
    }
    try {
      setLoadingMp3(true);
      setError(null);
      setMp3Result(null);
      setMp3Status('Submitting MP3 request...');
      // Assuming 'transcript' state holds the current editable content
      const response = await fetch(`${API_BASE_URL}/api/generate-mp3`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: repoMetadata?.name || fullRepoName, transcript: transcript }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      setMp3Status('MP3 generated. Upload complete.');
      const mp3Data = await response.json();
      setMp3Result(mp3Data);
      console.log('MP3 generation successful:', mp3Data);
    } catch (e) {
      setError(`Error generating MP3: ${e.message}`);
      setMp3Status('MP3 generation failed.');
      console.error('Error generating MP3:', e);
    } finally {
      setLoadingMp3(false);
    }
  };

  const handleGenerateVideo = async () => {
    if (!transcript || !transcript.trim()) {
      setError("Transcript is empty. Generate transcript first.");
      return;
    }
    try {
      setLoadingVideo(true);
      setError(null);
      setVideoJob(null);
      setVideoJobId(null);
      const response = await fetch(`${API_BASE_URL}/api/generate-video`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: repoMetadata?.name || fullRepoName,
          transcript: transcript,
          repo_context: repoContext || {},
          renderer_mode: rendererMode,
          video_prompt: videoPrompt,
          duration_seconds: durationSeconds,
          upload_to_sharepoint: uploadToSharePoint, // Include the new flag
        }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setVideoJobId(data.job_id);
    } catch (e) {
      setError(`Error generating video: ${e.message}`);
    } finally {
      setLoadingVideo(false);
    }
  };

  useEffect(() => {
    if (!videoJobId) return;
    let active = true;
    const poll = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/jobs/${videoJobId}`);
        if (!res.ok) return;
        const data = await res.json();
        if (!active) return;
        setVideoJob(data);
        if (data.status !== 'completed' && data.status !== 'failed') {
          setTimeout(poll, 2000);
        }
      } catch (e) {
        if (active) setTimeout(poll, 3000);
      }
    };
    poll();
    return () => {
      active = false;
    };
  }, [videoJobId, API_BASE_URL]);

  // Helper to render lists of strings
  const renderList = (items, label) => (
    items && items.length > 0 ? (
      <p className="text-gray-700 mb-1">
        <strong className="font-semibold">{label}:</strong> {items.join(', ')}
      </p>
    ) : null
  );

  // Helper to render table information
  const renderTableList = (tables, label) => (
    tables && tables.length > 0 ? (
      <div className="mb-1">
        <strong className="font-semibold">{label}:</strong>
        <ul className="list-disc list-inside pl-2">
          {tables.map((table, index) => (
            <li key={index} className="text-gray-700">
              {table.caption && `Caption: "${table.caption}" - `}Headers: {table.headers.join(', ')}
            </li>
          ))}
        </ul>
      </div>
    ) : null
  );

  if (loading) return <div className="text-center p-8">Loading repository metadata...</div>;

  return (
    <div className="container mx-auto p-4">
      <Link href="/demos" className="text-blue-600 hover:underline mb-4 inline-block">&larr; Back to Repositories</Link>
      <h1 className="text-3xl font-bold mb-4 text-gray-800">Editor for: {repoMetadata?.name || fullRepoName}</h1>
      <p className="text-gray-600 mb-6">{repoMetadata?.description || 'No description available.'}</p>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
          <strong className="font-bold">Error!</strong>
          <span className="block sm:inline"> {error}</span>
        </div>
      )}

      {repoMetadata && (
        <div className="bg-white rounded-lg shadow-md p-6 mb-6 border border-gray-200">
          <h3 className="text-xl font-semibold mb-3 text-gray-800">Repository Details</h3>
          <p className="text-gray-700 mb-1">
            <strong className="font-semibold">Full Name:</strong> {repoMetadata.full_name}
          </p>
          <p className="text-gray-700 mb-1">
            <strong className="font-semibold">Repo URL:</strong> <a href={repoMetadata.repo_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">{repoMetadata.repo_url}</a>
          </p>
          {repoMetadata.url && (
            <p className="text-gray-700 mb-1">
              <strong className="font-semibold">Live URL:</strong> <a href={repoMetadata.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">{repoMetadata.url}</a>
            </p>
          )}
          <p className="text-gray-700 mb-1">
            <strong className="font-semibold">Language:</strong> {repoMetadata.language || 'N/A'}
          </p>
          <p className="text-700 mb-1">
            <strong className="font-semibold">Visibility:</strong> {repoMetadata.private ? 'Private' : 'Public'}
          </p>
          <p className="text-gray-700 mb-1">
            <strong className="font-semibold">Last Updated:</strong> {new Date(repoMetadata.updated_at).toLocaleDateString()}
          </p>
        </div>
      )}

      <div className="mb-6">
        <button
          onClick={readRepoContext}
          className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded inline-flex items-center transition duration-150 ease-in-out mr-4"
          disabled={loadingRepoContext || !repoUrl}
        >
          {loadingRepoContext ? 'Reading Repo...' : 'Read Repo Context'}
        </button>
        <button
          onClick={generateTranscriptFromRepoContext}
          className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded inline-flex items-center transition duration-150 ease-in-out"
          disabled={loadingTranscript || !repoContext}
        >
          {loadingTranscript ? 'Generating...' : 'Generate Transcript from Repo Context'}
        </button>
      </div>

      {repoContext && (
        <div className="bg-white rounded-lg shadow-md p-6 mb-6 border border-blue-200">
          <h3 className="text-xl font-semibold mb-3 text-blue-800">Repository Context</h3>
          <p className="text-gray-700 mb-1">
            <strong className="font-semibold">Name:</strong> {repoContext.name || 'N/A'}
          </p>
          <p className="text-gray-700 mb-1">
            <strong className="font-semibold">Description:</strong> {repoContext.description || 'N/A'}
          </p>
          {renderList(repoContext.tech_stack, 'Detected Tech Stack')}
          {renderList(repoContext.features, 'Inferred Features')}
          {repoContext.readme && (
            <div className="mt-2">
              <strong className="font-semibold">README.md Preview:</strong>
              <p className="text-gray-700 whitespace-pre-wrap text-sm border p-2 rounded bg-gray-50 max-h-48 overflow-auto">
                {repoContext.readme}
              </p>
            </div>
          )}
        </div>
      )}
      
      {loadingTranscript && <div className="text-center p-8">Generating transcript...</div>}

      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <label htmlFor="transcript" className="block text-lg font-medium text-gray-700 mb-2">
          Editable Transcript
        </label>
        <textarea
          id="transcript"
          className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 transition duration-150 ease-in-out h-64 text-gray-800"
          value={transcript}
          onChange={(e) => setTranscript(e.target.value)}
        ></textarea>
      </div>

      <div className="flex flex-wrap gap-4">
        <button
          onClick={handleGenerateMp3}
          disabled={loadingMp3}
          className="bg-purple-600 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded transition duration-150 ease-in-out"
        >
          {loadingMp3 ? 'Generating MP3...' : 'Generate MP3'}
        </button>
        <button
          onClick={handleGenerateVideo}
          disabled={loadingVideo || (videoJob && (videoJob.status !== 'completed' && videoJob.status !== 'failed'))}
          className="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded transition duration-150 ease-in-out"
        >
          {loadingVideo ? 'Submitting Video Job...' : 'Generate Video'}
        </button>
      </div>
      <div className="mt-6 bg-white rounded-lg shadow-md p-6 border border-gray-200">
        <h3 className="text-xl font-semibold mb-3 text-gray-800">Video Renderer</h3>
        <div className="flex gap-6 mb-4">
          <label className="flex items-center gap-2">
            <input type="radio" checked={rendererMode === 'local_ffmpeg'} onChange={() => setRendererMode('local_ffmpeg')} />
            <span>Playwright + FFmpeg (Free)</span>
          </label>
          <label className="flex items-center gap-2">
            <input type="radio" checked={rendererMode === 'veo_lite'} onChange={() => setRendererMode('veo_lite')} />
            <span>Google Veo Lite (Paid)</span>
          </label>
        </div>
        <div className="flex items-center gap-4 mb-3">
          <label className="text-sm font-medium text-gray-700">Duration (seconds)</label>
          <input
            type="number"
            min={8}
            max={60}
            value={durationSeconds}
            onChange={(e) => setDurationSeconds(Math.max(8, Math.min(60, Number(e.target.value || 32))))}
            className="w-24 p-2 border border-gray-300 rounded-md"
          />
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={autoPromptMode} onChange={(e) => setAutoPromptMode(e.target.checked)} />
            <span>Auto prompt</span>
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={uploadToSharePoint} onChange={(e) => setUploadToSharePoint(e.target.checked)} />
            <span>Upload to SharePoint</span>
          </label>
        </div>
        <p className="text-sm text-gray-600 mb-2">Estimated Cost: ${rendererMode === 'veo_lite' ? (durationSeconds * 0.05).toFixed(2) : '0.00'}</p>
        {rendererMode === 'veo_lite' && (
          <p className="text-sm text-red-600 mb-3">Veo generation is chargeable. Use local mode for testing.</p>
        )}
        <label className="block text-md font-medium text-gray-700 mb-2">Editable Video Prompt</label>
        <textarea
          className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 h-40 text-gray-800"
          value={videoPrompt}
          onChange={(e) => setVideoPrompt(e.target.value)}
        />
      </div>
      {mp3Result && (
        <div className="mt-6 bg-green-100 border border-green-300 text-green-800 px-4 py-3 rounded">
          <p className="font-semibold mb-2">Media Outputs</p>
          <p><strong>Status:</strong> {mp3Status || 'Completed'}</p>
          <p><strong>MP3 generated:</strong> {mp3Result.local_file_name}</p>
          <p><strong>MP3 local path:</strong> {mp3Result.local_path}</p>
          <p><strong>GCS path:</strong> {mp3Result.gcs_path}</p>
        </div>
      )}
      {loadingMp3 && (
        <div className="mt-4 bg-blue-100 border border-blue-300 text-blue-900 px-4 py-3 rounded">
          <p><strong>MP3 Status:</strong> {mp3Status || 'Processing...'}</p>
        </div>
      )}
      {videoJob && (
        <div className="mt-4 bg-blue-100 border border-blue-300 text-blue-900 px-4 py-3 rounded">
          <p className="font-semibold mb-2">Video Job Progress</p>
          <p><strong>Video Job:</strong> {videoJob.job_id}</p>
          <p><strong>Status:</strong> {statusText[videoJob.status] || videoJob.status}</p>
          <p><strong>Message:</strong> {videoJob.message}</p>
          {videoJob.error && <p><strong>Error:</strong> {videoJob.error}</p>}
          {videoJob.result && (
            <div className="mt-2">
              <p><strong>MP3:</strong> {videoJob.result.mp3_file_name}</p>
              <p><strong>MP3 Local:</strong> {videoJob.result.mp3_local_path}</p>
              <p><strong>MP3 GCS:</strong> {videoJob.result.mp3_gcs_path}</p>
              <p><strong>Video:</strong> {videoJob.result.video_file_name}</p>
              <p><strong>Video Local:</strong> {videoJob.result.video_local_path}</p>
              <p><strong>Video GCS:</strong> {videoJob.result.video_gcs_path}</p>
              {videoJob.result.sharepoint_status && (
                <div className="mt-2 pt-2 border-t border-gray-200">
                  <p><strong>SharePoint Status:</strong> {videoJob.result.sharepoint_status}</p>
                  {videoJob.result.sharepoint_url && (
                    <p>
                      <strong className="font-semibold">SharePoint Link:</strong>{' '}
                      <a href={videoJob.result.sharepoint_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                        Open in SharePoint
                      </a>
                    </p>
                  )}
                  {videoJob.result.sharepoint_error && (
                    <p className="text-red-600"><strong>SharePoint Error:</strong> {videoJob.result.sharepoint_error}</p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
