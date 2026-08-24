import React from 'react';

export default function StatusBadge({ status, label, className = '' }) {
  const badgeStyles = {
    buy: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    sell: 'bg-red-500/15 text-red-400 border-red-500/30',
    passed: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    failed: 'bg-red-500/15 text-red-400 border-red-500/30',
    warning: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
    neutral: 'bg-slate-500/15 text-slate-400 border-slate-500/30'
  };

  const key = (status || 'neutral').toLowerCase();
  const appliedStyle = badgeStyles[key] || badgeStyles.neutral;

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[0.75rem] font-bold uppercase border ${appliedStyle} ${className}`}>
      {label || status}
    </span>
  );
}
