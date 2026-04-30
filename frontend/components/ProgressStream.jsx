'use client';

import { useEffect, useRef, useState } from 'react';

export default function ProgressStream({ apiBaseUrl, jobId, onFinal }) {
  const [events, setEvents] = useState([]);
  const [percent, setPercent] = useState(0);
  const esRef = useRef(null);

  useEffect(() => {
    if (!jobId) return;
    const streamUrl = `${apiBaseUrl}/api/generate-readme/${jobId}/stream`;
    const es = new EventSource(streamUrl);
    esRef.current = es;

    es.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);
        setEvents((prev) => [...prev, data]);
        if (typeof data.percent === 'number') setPercent(data.percent);
        if (data.stage === 'result') {
          onFinal?.(data);
          es.close();
        }
      } catch {
        // ignore malformed chunks
      }
    };

    es.onerror = () => {
      es.close();
    };

    return () => {
      es.close();
    };
  }, [apiBaseUrl, jobId, onFinal]);

  return (
    <div style={{ border: '1px solid #ddd', padding: 12, borderRadius: 8 }}>
      <div style={{ marginBottom: 8, fontWeight: 600 }}>Progress: {percent}%</div>
      <div style={{ background: '#f1f1f1', height: 8, borderRadius: 999 }}>
        <div style={{ width: `${percent}%`, height: '100%', background: '#0d9488', borderRadius: 999 }} />
      </div>
      <div style={{ marginTop: 12, maxHeight: 200, overflowY: 'auto', fontSize: 13 }}>
        {events.map((e, idx) => (
          <div key={idx} style={{ padding: '4px 0', borderBottom: '1px solid #f3f3f3' }}>
            <strong>{e.stage || 'event'}</strong>: {e.message || e.status || '...'}
          </div>
        ))}
      </div>
    </div>
  );
}
