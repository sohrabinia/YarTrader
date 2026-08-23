import React from 'react';

export default function TimelineStepper({ steps = [], activeStep = 0, className = '' }) {
  return (
    <div className={`grid grid-cols-1 sm:grid-cols-5 gap-3 ${className}`}>
      {steps.map((step, idx) => {
        const isCurrent = idx === activeStep;
        const isCompleted = idx < activeStep;
        return (
          <div
            key={idx}
            className={`p-3 rounded-lg border text-left transition-all ${
              isCurrent
                ? 'bg-amber-500/10 border-[var(--primary)]'
                : isCompleted
                ? 'bg-emerald-500/10 border-emerald-500/30'
                : 'bg-slate-900/40 border-[var(--border-dark)] opacity-60'
            }`}
          >
            <div className="text-[0.7rem] text-[var(--text-muted)] font-mono">{idx + 1}. {step.label}</div>
            <div className="text-xs font-bold mt-1 text-[var(--text-dark)]">{step.value || 'DATA UNAVAILABLE'}</div>
            {step.sub && <div className="text-[0.68rem] text-[var(--text-muted)] mt-0.5">{step.sub}</div>}
          </div>
        );
      })}
    </div>
  );
}
