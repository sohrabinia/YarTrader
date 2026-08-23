import React from 'react';

export default function LoadingSkeleton({ rows = 3, height = 'h-10', className = '' }) {
  return (
    <div className={`flex flex-col gap-2 w-full animate-pulse ${className}`}>
      {Array.from({ length: rows }).map((_, idx) => (
        <div key={idx} className={`w-full ${height} bg-slate-800/60 rounded border border-[var(--border-dark)]`} />
      ))}
    </div>
  );
}
