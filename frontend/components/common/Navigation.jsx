'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const items = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/generate', label: 'Generate' },
  { href: '/history', label: 'History' },
  { href: '/settings', label: 'Settings' },
];

export default function Navigation() {
  const path = usePathname();
  return (
    <nav className='panel' style={{ marginBottom: 16, padding: 8, display: 'flex', gap: 8, overflowX: 'auto' }}>
      {items.map((i) => (
        <Link key={i.href} href={i.href} className='btn' style={{ background: path === i.href ? 'var(--primary)' : 'var(--panel)', color: path === i.href ? '#fff' : 'var(--text)' }}>
          {i.label}
        </Link>
      ))}
    </nav>
  );
}
