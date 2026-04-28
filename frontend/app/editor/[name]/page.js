'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams, useSearchParams } from 'next/navigation'; // Import useSearchParams
import Link from 'next/link';

export default function EditorPage() {
  const params = useParams();
  const searchParams = useSearchParams(); // Get search params
  const fullRepoName = params.name; // This will be owner/repo
  const repoUrl = searchParams.get('repo_url'); // Get repo_url from query params

  const [repoMetadata, setRepoMetadata] = useState(null);
  const [repoContext, setRepoContext] = useState(null); // This will hold the result of POST /api/repo-context
  const [transcript, setTranscript] = useState('');
  const [showSourceContext, setShowSourceContext] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [loadingRepoContext, setLoadingRepoContext] = useState(false);
  const [loadingTranscript, setLoadingTranscript] = useState(false);

  const API_BASE_URL = 'http://10.100.15.44:8000'; // Define API base URL

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
      setSourceContext(transcriptData.source_context); // Update main sourceContext
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

  // If repo metadata is loaded and repoUrl is available, attempt to read context automatically
  // useEffect(() => {
  //   if (repoMetadata && repoUrl && !repoContext && !loadingRepoContext) {
  //     readRepoContext();
  //   }
  // }, [repoMetadata, repoUrl, repoContext, loadingRepoContext, readRepoContext]);


  const handleGenerateMp3 = async () => {
    alert('Generating MP3...'); // User feedback
    try {
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

      const mp3Data = await response.json();
      alert(`MP3 Generated!\nFilename: ${mp3Data.local_file_name}\nGCS Path: ${mp3Data.gcs_path}`);
      console.log('MP3 generation successful:', mp3Data);
    } catch (e) {
      alert(`Error generating MP3: ${e.message}`);
      console.error('Error generating MP3:', e);
    }
  };

  const handleGenerateVideo = () => {
    alert('Generate Video clicked!');
    // In a real app, this would trigger a backend call to generate Video
  };

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
          className="bg-purple-600 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded transition duration-150 ease-in-out"
        >
          Generate MP3
        </button>
        <button
          onClick={handleGenerateVideo}
          className="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded transition duration-150 ease-in-out"
        >
          Generate Video
        </button>
      </div>
    </div>
  );
}
