import React from 'react';

export default function MetricCard({ title, value, status = 'neutral', subtitle, sparkline, className = '' }) {
  const statusColors = {
    passed: 'text-[var(--accent)]',
    failed: 'text-[var(--danger)]',
    warn: 'text-[var(--warning)]',
    neutral: 'text-[var(--text-dark)]',
    primary: 'text-[var(--primary)]'
  };

  return (
    <div className={`status-item bg-slate-900/40 border border-[var(--border-dark)] p-4 rounded-lg text-center transition-all ${className}`}>
      <div className="text-xs text-[var(--text-muted)] font-medium mb-1">{title}</div>
      <div className={`status-val font-mono font-bold text-xl ${statusColors[status] || statusColors.neutral}`}>
        {value != null ? value : 'DATA UNAVAILABLE'}
      </div>
      {subtitle && <div className="text-[0.75rem] text-[var(--text-muted)] mt-1">{subtitle}</div>}
      {sparkline && <div className="mt-2 text-xs font-mono text-[var(--primary)]">{sparkline}</div>}
    </div>
  );
}
