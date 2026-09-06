import React from 'react';

export function Badge({ children, variant = 'neutral', className = '', ...props }) {
  const variantStyles = {
    passed: 'bg-[var(--accent)]/15 text-[var(--accent)] border-[var(--accent)]/30',
    failed: 'bg-[var(--danger)]/15 text-[var(--danger)] border-[var(--danger)]/30',
    warning: 'bg-[var(--warning)]/15 text-[var(--warning)] border-[var(--warning)]/30',
    primary: 'bg-[var(--primary)]/15 text-[var(--primary)] border-[var(--primary)]/30',
    neutral: 'bg-[var(--surface-light)] text-[var(--text-muted)] border-[var(--border-dark)]'
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${variantStyles[variant] || variantStyles.neutral} ${className}`.trim()}
      {...props}
    >
      {children}
    </span>
  );
}
