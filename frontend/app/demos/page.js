'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

export default function DemosPage() {
  const [apps, setApps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchApps() {
      try {
        const response = await fetch('http://localhost:8000/api/apps');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setApps(data);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    fetchApps();
  }, []);

  if (loading) return <div className="text-center p-8">Loading apps...</div>;
  if (error) return <div className="text-center p-8 text-red-500">Error: {error}</div>;

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-6 text-gray-800">Available Demos</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {apps.map((app) => (
          <div key={app.name} className="bg-white rounded-lg shadow-md p-6 flex flex-col justify-between">
            <div>
              <h2 className="text-xl font-semibold mb-2 text-gray-900">{app.name.replace(/_/g, ' ').replace(/\b\w/g, char => char.toUpperCase())}</h2>
              <p className="text-gray-600 mb-4">{app.description}</p>
            </div>
            <Link href={`/editor/${app.name}`} className="inline-block bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded text-center transition duration-150 ease-in-out">
              Open
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
}
