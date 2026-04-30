'use client';
export default function ThemeToggle({ theme, setTheme }) {
  return <button aria-label='Toggle theme' className='btn focusable' onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>{theme === 'dark' ? '☀️' : '🌙'}</button>;
}
