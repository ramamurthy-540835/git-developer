'use client';
import { useState } from 'react';
export default function UserMenu({ user }) {
  const [open, setOpen] = useState(false);
  return <div style={{ position: 'relative' }}>
    <button aria-label='User menu' className='btn focusable' onClick={() => setOpen((v) => !v)}>{user?.login?.[0]?.toUpperCase() || 'U'}</button>
    {open && <div className='card' style={{ position: 'absolute', right: 0, top: 44, minWidth: 160, padding: 8 }}>
      <a href='/settings'>Settings</a>
    </div>}
  </div>;
}
