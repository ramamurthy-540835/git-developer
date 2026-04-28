'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';

export default function EditorPage() {
  const params = useParams();
  const appName = params.name;
  const [transcript, setTranscript] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchTranscript() {
      try {
        setLoading(true);
        const response = await fetch(`/api/transcript?name=${appName}`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setTranscript(data.transcript);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    fetchTranscript();
  }, [appName]);

  const handleRegenerate = () => {
    alert('Regenerate Transcript clicked!');
    // In a real app, this would trigger a backend call to regenerate
  };

  const handleGenerateMp3 = () => {
    alert('Generate MP3 clicked!');
    // In a real app, this would trigger a backend call to generate MP3
  };

  const handleGenerateVideo = () => {
    alert('Generate Video clicked!');
    // In a real app, this would trigger a backend call to generate Video
  };

  if (loading) return <div className="text-center p-8">Loading transcript...</div>;
  if (error) return <div className="text-center p-8 text-red-500">Error: {error}</div>;

  return (
    <div className="container mx-auto p-4">
      <Link href="/demos" className="text-blue-600 hover:underline mb-4 inline-block">&larr; Back to Demos</Link>
      <h1 className="text-3xl font-bold mb-6 text-gray-800">Editor for: {appName.replace(/_/g, ' ').replace(/\b\w/g, char => char.toUpperCase())}</h1>

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
