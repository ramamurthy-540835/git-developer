'use client';
import { useEffect } from 'react';

export default function ToastNotification({ message, onDone, tone = 'success' }) {
  useEffect(() => {
    if (!message) return undefined;
    const t = setTimeout(() => onDone?.(), 5000);
    return () => clearTimeout(t);
  }, [message, onDone]);

  if (!message) return null;
  return <div className={`toast ${tone}`} role='status' aria-live='polite'>{message}</div>;
}
