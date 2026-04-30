export default function Home() {
  return (
    <main style={{ maxWidth: 900, margin: '32px auto', padding: '0 16px', fontFamily: 'ui-sans-serif, system-ui' }}>
      <h1 style={{ fontSize: 32, marginBottom: 12 }}>git-developer</h1>
      <p style={{ marginBottom: 16 }}>
        README generation platform for GitHub repositories.
      </p>
      <a href="/generate" style={{ display: 'inline-block', padding: '10px 14px', border: '1px solid #111', borderRadius: 8, textDecoration: 'none' }}>
        Open Generate UI
      </a>
    </main>
  );
}
