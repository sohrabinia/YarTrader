import React from 'react';

export default function HealthIndicator({ state, label, className = '' }) {
  const isOnline = state === 'LIVE' || state === 'DEMO' || state === 'ONLINE';
  const isDemo = state === 'DEMO';
  const isUnreachable = state === 'UNREACHABLE' || state === 'OFFLINE';

  const bgColor = isOnline
    ? isDemo ? 'bg-amber-500 text-slate-950' : 'bg-emerald-500 text-slate-950'
    : isUnreachable ? 'bg-red-500 text-white' : 'bg-slate-500 text-white';

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-bold font-mono ${bgColor} ${className}`}>
      <span className="w-2 h-2 rounded-full bg-current animate-pulse"></span>
      <span>{label || state}</span>
    </span>
  );
}
