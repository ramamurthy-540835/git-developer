'use client';
import dynamic from 'next/dynamic';
const ReactDiffViewer = dynamic(() => import('react-diff-viewer-continued'), { ssr: false });

export default function ComparisonView({ originalText, newText }) {
  if (!originalText || !newText) return null;
  return <section className='panel' style={{ padding: 16 }}>
    <h3>Comparison View</h3>
    <ReactDiffViewer oldValue={originalText} newValue={newText} splitView />
  </section>;
}
