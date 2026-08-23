import React from 'react';

export default function PositionTimelineStepper({ currentState = 'CREATED', retcode, timestamps = {}, className = '' }) {
  const steps = [
    { key: 'CREATED', label: '1. CREATED', sub: timestamps.created || 'Signal Generated' },
    { key: 'VALIDATED', label: '2. VALIDATED', sub: timestamps.validated || 'Risk Approved' },
    { key: 'OPENED', label: '3. OPENED', sub: timestamps.opened || 'Order Dispatched' },
    { key: 'MANAGED', label: '4. MANAGED', sub: timestamps.managed || 'SL/TP Monitored' },
    { key: 'CLOSED', label: '5. CLOSED', sub: timestamps.closed || `Retcode: ${retcode || '10009 OK'}` }
  ];

  const stateOrder = ['CREATED', 'VALIDATED', 'OPENED', 'MANAGED', 'CLOSED'];
  const activeIdx = stateOrder.indexOf(currentState.toUpperCase());

  return (
    <div className={`grid grid-cols-1 sm:grid-cols-5 gap-2 my-2 ${className}`}>
      {steps.map((step, idx) => {
        const isCurrent = idx === activeIdx;
        const isCompleted = idx < activeIdx;
        return (
          <div
            key={idx}
            className={`p-2 rounded border text-center text-xs font-mono transition-all ${
              isCurrent
                ? 'bg-amber-500/15 border-[var(--primary)] text-[var(--primary)] font-bold'
                : isCompleted
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                : 'bg-slate-900/40 border-[var(--border-dark)] text-slate-500'
            }`}
          >
            <div>{step.label}</div>
            <div className="text-[0.65rem] opacity-80 mt-0.5">{step.sub}</div>
          </div>
        );
      })}
    </div>
  );
}
