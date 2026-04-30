'use client';
import ThemeToggle from './ThemeToggle';

export default function Header() {
  return (
    <header className='panel' style={{ margin: '12px 0', padding: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
        <div>
          <div style={{ fontWeight: 800, fontSize: 20 }}>git-developer README Generator</div>
          <div style={{ color: 'var(--muted)', fontSize: 13 }}>AI-powered professional READMEs in seconds</div>
        </div>
        <ThemeToggle />
      </div>
    </header>
  );
}
