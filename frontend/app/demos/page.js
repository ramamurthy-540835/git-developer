'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

export default function DemosPage() {
  const [repos, setRepos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filteredRepos, setFilteredRepos] = useState([]);

  const API_BASE_URL = 'http://localhost:8000'; // Define API base URL

  useEffect(() => {
    async function fetchRepos() {
      try {
        const response = await fetch(`${API_BASE_URL}/api/repos`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setRepos(data.repos); // Assuming the backend returns { "repos": [...] }
        setFilteredRepos(data.repos);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    fetchRepos();
  }, []);

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
          <p className="col-span-full text-center text-gray-500">No repositories found matching your criteria.</p>
        )}
      </div>
    </div>
  );
}
