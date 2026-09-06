import React from 'react';

export function Input({ className = '', type = 'text', ...props }) {
  return (
    <input
      type={type}
      className={`flex h-10 w-full rounded-md border border-[var(--border-dark)] bg-[var(--surface-light)] px-3 py-2 text-sm ring-offset-background placeholder:text-[var(--text-muted)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary)] disabled:cursor-not-allowed disabled:opacity-50 text-[var(--text-dark)] ${className}`.trim()}
      {...props}
    />
  );
}
