import React from 'react';

export default function IntelligenceCard({ symbol, posture, timeframe, confidence, narrative, entry, target, invalidation, className = '' }) {
  const isBullish = posture === 'BULLISH' || posture === 'BUY';
  return (
    <div className={`status-item p-5 rounded-lg border-r-4 ${isBullish ? 'border-r-[var(--accent)]' : 'border-r-[var(--danger)]'} bg-slate-900/40 border border-[var(--border-dark)] ${className}`}>
      <div className="flex justify-between items-center mb-2">
        <span className="font-bold text-[var(--text-dark)]">{symbol}</span>
        <span className={`status-val text-xs px-2 py-0.5 rounded font-mono font-bold ${isBullish ? 'status-passed bg-emerald-500/10' : 'status-failed bg-red-500/10'}`}>
          {posture || 'QUALIFIED'}
        </span>
      </div>
      <div className="text-xs text-[var(--text-muted)] mb-2">
        Frame: {timeframe || 'H1'} | Confidence: <span className="font-mono font-bold text-[var(--primary)]">{confidence != null ? `${confidence}%` : 'N/A'}</span>
      </div>
      {entry && <div className="text-xs font-mono mb-1"><strong>Entry:</strong> {entry}</div>}
      {target && <div className="text-xs font-mono mb-1 text-[var(--accent)]"><strong>Target:</strong> {target}</div>}
      {invalidation && <div className="text-xs font-mono mb-1 text-[var(--danger)]"><strong>Invalidation:</strong> {invalidation}</div>}
      <p className="text-xs text-[var(--text-dark)] mt-2 pt-2 border-t border-[var(--border-dark)] leading-relaxed">
        {narrative || 'No setup description.'}
      </p>
    </div>
  );
}
