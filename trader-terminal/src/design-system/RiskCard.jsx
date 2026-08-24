import React from 'react';

export default function RiskCard({ heat, riskBudget, drawdownLevel, approved = true, className = '' }) {
  return (
    <div className={`card border border-[var(--border-dark)] bg-[var(--surface-dark)] p-5 rounded-lg shadow-md ${className}`}>
      <h3 className="m-0 text-[var(--primary)] font-bold text-lg mb-2">🛡️ Portfolio Risk Board</h3>
      <p className="text-xs text-[var(--text-muted)] mb-4">Enforces risk controls on asset concentration and correlation heat.</p>

      <div className="flex flex-col gap-3 mb-4">
        <div className="status-item p-3 text-left">
          <div className="text-xs text-[var(--text-muted)]">Portfolio Heat</div>
          <div className="status-val text-red-400 font-mono text-base">{heat || 'DATA UNAVAILABLE'}</div>
        </div>
        <div className="status-item p-3 text-left">
          <div className="text-xs text-[var(--text-muted)]">Risk Budget Remaining</div>
          <div className="status-val text-[var(--accent)] font-mono text-base">{riskBudget || 'DATA UNAVAILABLE'}</div>
        </div>
        <div className="status-item p-3 text-left">
          <div className="text-xs text-[var(--text-muted)]">Drawdown Risk Level</div>
          <div className="status-val text-[var(--warning)] font-mono text-base">{drawdownLevel || 'BALANCED'}</div>
        </div>
        <div className="status-item p-3 text-left">
          <div className="text-xs text-[var(--text-muted)]">SRE Risk Approved</div>
          <div className="status-val status-passed font-mono text-base">{approved ? 'APPROVED' : 'BLOCKED'}</div>
        </div>
      </div>
    </div>
  );
}
