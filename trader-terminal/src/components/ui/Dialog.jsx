import React from 'react';

export function Dialog({ open, onClose, children, title }) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-lg rounded-xl border border-[var(--border-dark)] bg-[var(--surface-dark)] p-6 shadow-2xl animate-in fade-in zoom-in-95">
        <div className="flex items-center justify-between pb-4 border-b border-[var(--border-dark)] mb-4">
          {title && <h3 className="text-lg font-bold text-[var(--primary)]">{title}</h3>}
          <button
            onClick={onClose}
            className="text-[var(--text-muted)] hover:text-[var(--text-dark)] text-xl font-bold p-1 cursor-pointer"
            aria-label="Close dialog"
          >
            ✕
          </button>
        </div>
        <div>{children}</div>
      </div>
    </div>
  );
}
