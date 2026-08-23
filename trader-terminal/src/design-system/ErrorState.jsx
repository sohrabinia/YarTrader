import React from 'react';

export default function ErrorState({ title = 'Error Occurred', message, onRetry, className = '' }) {
  return (
    <div className={`p-4 bg-red-500/10 border border-[var(--danger)] text-[var(--danger)] text-xs rounded-lg flex items-center justify-between gap-3 ${className}`}>
      <div>
        <strong className="block text-sm font-bold mb-0.5">⚠️ {title}</strong>
        <span>{message || 'An unexpected error occurred while communicating with the backend.'}</span>
      </div>
      {onRetry && (
        <button
          type="button"
          className="btn btn-secondary text-xs whitespace-nowrap border-red-500/30 hover:bg-red-500/20"
          onClick={onRetry}
        >
          Retry 🔄
        </button>
      )}
    </div>
  );
}
