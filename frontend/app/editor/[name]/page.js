'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';

export default function EditorPage() {
  const params = useParams();
  const appName = params.name;
  const [transcript, setTranscript] = useState('');
  const [sourceContext, setSourceContext] = useState(null);
  const [showSourceContext, setShowSourceContext] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Function to fetch transcript from the backend API
  const fetchTranscript = useCallback(async () => {
    try {
      setLoading(true);
      setError(null); // Clear previous errors
      setSourceContext(null); // Clear previous source context

      // This is a simplification; ideally, the app's full object is passed from /demos or fetched via /api/apps/{name}.
      // For now, construct a plausible mock URL and description based on appName.
      // NOTE: This URL construction is a *mock* and assumes a predictable Cloud Run URL pattern.
      // In a real scenario, you'd fetch the full app details from /api/apps/[name] first or pass it from /demos.
      const appData = {
        name: appName,
        url: `https://${appName.toLowerCase().replace(/_/g, '-')}-1035117862188.us-central1.run.app`,
        description: `A demo application for ${appName.replace(/_/g, ' ').replace(/\b\w/g, char => char.toUpperCase())}.`,
        // Add tags here if needed in the future
      };

      // Frontend Next.js API route is `/api/transcript`, but the actual backend Flask API is `http://localhost:5000/api/transcript`
      // When deployed, Next.js could proxy this, or the Flask app could be on the same domain.
      // For local development, we're calling the Flask backend directly.
      const response = await fetch('http://10.100.15.44:8000/api/transcript', { // Use explicit IP for FastAPI backend
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ app: appData }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.details || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setTranscript(data.transcript);
      setSourceContext(data.source_context);
      // Display backend warning if present
      if (data.warning) {
        setError(data.warning); // Use error state to display the warning
      }
    } catch (e) {
      console.error("Error fetching transcript:", e);
      setError(e.message);
      setTranscript(`Failed to load transcript. Please regenerate or check the console for errors.`); // Generic user-friendly message
      setSourceContext(null); // Clear context on error
    } finally {
      setLoading(false);
    }
  }, [appName]); // Re-create if appName changes

  useEffect(() => {
    fetchTranscript();
  }, [fetchTranscript]); // Depend on memoized fetchTranscript

  const handleRegenerate = () => {
    fetchTranscript(); // Re-fetch transcript with current appName
  };

  const handleGenerateMp3 = async () => {
    alert('Generating MP3...'); // User feedback
    try {
      // Assuming 'transcript' state holds the current editable content
      const response = await fetch('http://10.100.15.44:8000/api/generate-mp3', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: appName, transcript: transcript }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      alert(`MP3 Generated!\nFilename: ${data.local_file_name}\nGCS Path: ${data.gcs_path}`);
      console.log('MP3 generation successful:', data);
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

  return (
    <div className="container mx-auto p-4">
      <Link href="/demos" className="text-blue-600 hover:underline mb-4 inline-block">&larr; Back to Demos</Link>
      <h1 className="text-3xl font-bold mb-6 text-gray-800">Editor for: {appName.replace(/_/g, ' ').replace(/\b\w/g, char => char.toUpperCase())}</h1>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
          <strong className="font-bold">Error!</strong>
          <span className="block sm:inline"> {error}</span>
        </div>
      )}

      {loading && <div className="text-center p-8">Loading transcript and page context...</div>}

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

      <div className="mb-6">
        <button
          onClick={() => setShowSourceContext(!showSourceContext)}
          className="bg-gray-200 hover:bg-gray-300 text-gray-800 font-bold py-2 px-4 rounded inline-flex items-center transition duration-150 ease-in-out"
        >
          {showSourceContext ? 'Hide' : 'Show'} Source Page Context
          <svg className={`ml-2 w-4 h-4 transition-transform duration-200 ${showSourceContext ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
        </button>

        {showSourceContext && sourceContext && (
          <div className="bg-white rounded-lg shadow-md p-6 mt-4 border border-gray-200">
            <h3 className="text-xl font-semibold mb-3 text-gray-800">Source Page Context</h3>
            <p className="text-gray-700 mb-1">
              <strong className="font-semibold">Page Title:</strong> {sourceContext.title || 'N/A'}
            </p>
            <p className="text-gray-700 mb-1">
              <strong className="font-semibold">URL:</strong> <a href={sourceContext.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">{sourceContext.url}</a>
            </p>
            {renderList(sourceContext.headings, 'Headings')}
            {renderList(sourceContext.buttons, 'Buttons')}
            {renderList(sourceContext.cards, 'Card Titles')}
            {renderTableList(sourceContext.tables, 'Tables')}

            {/* Display message if no specific content was found or if there was a reading error */}
            {sourceContext.url && sourceContext.headings.length === 0 && sourceContext.buttons.length === 0 && sourceContext.cards.length === 0 && sourceContext.tables.length === 0 && (
                <p className="text-sm text-gray-500 mt-2">No specific visible content (headings, buttons, cards, tables) found on the page.</p>
            )}
            {/* If there's an error from the backend, it will be displayed by the main error alert.
                This section now shows only context, not the warning message itself. */}
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-4">
        <button
          onClick={handleRegenerate}
          className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded transition duration-150 ease-in-out"
        >
          Regenerate Transcript
        </button>
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
