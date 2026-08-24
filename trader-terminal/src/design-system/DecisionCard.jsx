import React from 'react';

export default function DecisionCard({ action, entry, stopLoss, takeProfit, riskReward, confidence, reasoning = [], className = '' }) {
  return (
    <div className={`card border border-[var(--border-dark)] bg-[var(--surface-dark)] p-5 rounded-lg shadow-md ${className}`}>
      <h3 className="m-0 text-[var(--primary)] font-bold text-lg mb-2">🎯 Advisory Trade Decision Plan</h3>
      <div className="status-board mb-4">
        <div className="status-item">
          <div className="text-xs text-[var(--text-muted)]">Action</div>
          <div className="status-val text-[var(--accent)] font-bold">{action || 'DATA UNAVAILABLE'}</div>
        </div>
        <div className="status-item">
          <div className="text-xs text-[var(--text-muted)]">Advisory Entry</div>
          <div className="status-val font-mono text-[var(--text-dark)]">{entry || '-'}</div>
        </div>
        <div className="status-item">
          <div className="text-xs text-[var(--text-muted)]">Stop Loss</div>
          <div className="status-val font-mono text-[var(--danger)]">{stopLoss || '-'}</div>
        </div>
        <div className="status-item">
          <div className="text-xs text-[var(--text-muted)]">Take Profit</div>
          <div className="status-val font-mono text-[var(--accent)]">{takeProfit || '-'}</div>
        </div>
        <div className="status-item">
          <div className="text-xs text-[var(--text-muted)]">Risk / Reward</div>
          <div className="status-val font-mono text-[var(--primary)]">{riskReward || '-'}</div>
        </div>
      </div>

      {reasoning && reasoning.length > 0 && (
        <div>
          <h4 className="text-xs font-bold text-[var(--primary)] uppercase tracking-wider mb-2">Reasoning Trace (XAI)</h4>
          <ul className="text-xs text-[var(--text-muted)] leading-relaxed pl-5 list-disc">
            {reasoning.map((r, idx) => (
              <li key={idx}>{r}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
