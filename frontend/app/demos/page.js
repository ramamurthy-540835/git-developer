'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

export default function DemosPage() {
  const [repos, setRepos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filteredRepos, setFilteredRepos] = useState([]);

  const fallbackApiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL
    ? process.env.NEXT_PUBLIC_API_BASE_URL.replace(/\/api\/v1\/?$/, "").replace(/\/$/, "")
    : "";

  useEffect(() => {
    async function fetchRepos() {
      const primaryUrl = "/api/repos";
      const fallbackUrl = fallbackApiBaseUrl ? `${fallbackApiBaseUrl}/api/repos` : null;
      try {
        setLoading(true);
        setError(null); // Clear previous errors
        let response;
        let lastUrl = primaryUrl;
        try {
          response = await fetch(primaryUrl);
        } catch {
          if (!fallbackUrl) throw new Error(`Failed to fetch ${primaryUrl}`);
          lastUrl = fallbackUrl;
          response = await fetch(fallbackUrl);
        }
        if (!response.ok) {
          const errorDetail = await response.text();
          throw new Error(`HTTP error! Status: ${response.status}. URL: ${lastUrl}. Detail: ${errorDetail}`);
        }
        const data = await response.json();
        console.log("Repos API response:", data);
        const repoList = Array.isArray(data) ? data : data.repos || [];
        setRepos(repoList);
        setFilteredRepos(repoList);
      } catch (e) {
        console.error("Fetch repos failed:", e);
        setError(`Failed to fetch repositories: ${e.message}`);
      } finally {
        setLoading(false);
      }
    }
    fetchRepos();
  }, [fallbackApiBaseUrl]);

  useEffect(() => {
    const lowerCaseSearchTerm = searchTerm.toLowerCase();
    const results = repos.filter(repo =>
      repo.name.toLowerCase().includes(lowerCaseSearchTerm) ||
      repo.full_name.toLowerCase().includes(lowerCaseSearchTerm) ||
      (repo.language && repo.language.toLowerCase().includes(lowerCaseSearchTerm)) ||
      (repo.description && repo.description.toLowerCase().includes(lowerCaseSearchTerm))
    );
    setFilteredRepos(results);
  }, [searchTerm, repos]);

  if (loading) return <div className="text-center p-8">Loading repositories...</div>;
  if (error) return <div className="text-center p-8 text-red-500">Error: {error}</div>;

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-6 text-gray-800">Available Repositories</h1>
      
      <input
        type="text"
        placeholder="Search repositories by name, language, or description..."
        className="w-full p-3 border border-gray-300 rounded-md mb-6 focus:outline-none focus:ring-2 focus:ring-blue-500 transition duration-150 ease-in-out"
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
      />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredRepos.length > 0 ? (
          filteredRepos.map((repo) => (
            <div key={repo.full_name} className="bg-white rounded-lg shadow-md p-6 flex flex-col justify-between">
              <div>
                <h2 className="text-xl font-semibold mb-1 text-gray-900">{repo.name}</h2>
                <p className="text-sm text-gray-500 mb-2">{repo.full_name}</p>
                <p className="text-gray-600 mb-4 text-sm">{repo.description || 'No description available.'}</p>
                <div className="text-xs text-gray-500 mb-4">
                  <span>Language: <span className="font-semibold">{repo.language || 'N/A'}</span></span>
                  <span className="ml-4">Status: <span className="font-semibold">{repo.private ? 'Private' : 'Public'}</span></span>
                  <span className="ml-4">Updated: <span className="font-semibold">{new Date(repo.updated_at).toLocaleDateString()}</span></span>
                </div>
              </div>
              <Link 
                href={`/editor/${encodeURIComponent(repo.full_name)}?repo_url=${encodeURIComponent(repo.repo_url)}`} 
                className="inline-block bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded text-center transition duration-150 ease-in-out"
              >
                Open Editor
              </Link>
            </div>
          ))
        ) : (
          <p className="col-span-full text-center text-gray-500">No repositories found.</p>
        )}
      </div>
    </div>
  );
}
