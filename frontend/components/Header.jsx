'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import ThemeToggle from './common/ThemeToggle';
import UserMenu from './common/UserMenu';
import { useAppStore } from '../store/useAppStore';

export default function Header() {
  const path = usePathname();
  const { theme, setTheme, user } = useAppStore();
  const tabs = [{ href: '/dashboard', label: 'Dashboard' }, { href: '/generate', label: 'Generate' }, { href: '/history', label: 'History' }, { href: '/settings', label: 'Settings' }];
  return <header className='topbar'>
    <div className='topbar-inner'>
      <div className='brand'><span aria-hidden>⑂</span><span>git-developer</span></div>
      <nav className='nav'>{tabs.map((t) => <Link key={t.href} href={t.href} className={path === t.href ? 'active' : ''}>{t.label}</Link>)}</nav>
      <div className='header-actions'><ThemeToggle theme={theme} setTheme={setTheme} /><UserMenu user={user} /></div>
    </div>
  </header>;
}
