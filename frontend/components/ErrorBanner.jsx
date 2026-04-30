'use client';
import { useEffect } from 'react';

export default function ErrorBanner({ message, onDismiss, autoDismissMs = 5000 }) {
  useEffect(() => {
    if (!message) return undefined;
    const t = setTimeout(() => onDismiss?.(), autoDismissMs);
    return () => clearTimeout(t);
  }, [message, onDismiss, autoDismissMs]);

  if (!message) return null;
  return (
    <div role='alert' className='error-banner'>
      <span>❌ {message}</span>
      <button aria-label='Dismiss error' className='btn' onClick={onDismiss}>✕</button>
    </div>
  );
}
