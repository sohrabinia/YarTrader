import React from 'react';

export default function DataTable({ headers = [], rows = [], emptyMessage = 'No data records found.', className = '' }) {
  return (
    <div className={`overflow-x-auto w-full ${className}`}>
      <table className="w-full border-collapse mt-2 text-left">
        <thead>
          <tr className="bg-slate-800/40 text-[var(--text-muted)] text-xs font-bold border-b border-[var(--border-dark)]">
            {headers.map((h, idx) => (
              <th key={idx} className="p-3">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="text-xs text-[var(--text-dark)] font-mono num-tabular">
          {rows && rows.length > 0 ? (
            rows.map((row, rIdx) => (
              <tr key={rIdx} className="border-b border-[var(--border-dark)] hover:bg-white/[0.02]">
                {row.map((cell, cIdx) => (
                  <td key={cIdx} className="p-3">{cell}</td>
                ))}
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={headers.length || 1} className="p-6 text-center text-[var(--text-muted)]">
                {emptyMessage}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
