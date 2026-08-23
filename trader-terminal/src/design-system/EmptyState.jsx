import React from 'react';

export default function EmptyState({ icon = '🔍', title = 'No Data Found', description, actionLabel, onAction, className = '' }) {
  return (
    <div className={`p-8 text-center bg-slate-900/30 border border-[var(--border-dark)] rounded-lg ${className}`}>
      <div className="text-3xl mb-2">{icon}</div>
      <div className="font-bold text-sm text-[var(--text-dark)] mb-1">{title}</div>
      {description && <p className="text-xs text-[var(--text-muted)] max-w-sm mx-auto mb-4">{description}</p>}
      {actionLabel && onAction && (
        <button type="button" className="btn text-xs px-4 py-1.5" onClick={onAction}>
          {actionLabel}
        </button>
      )}
    </div>
  );
}
