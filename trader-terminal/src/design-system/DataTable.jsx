import React from 'react';

export default function DataTable({ headers, rows, columns, data, emptyMessage = 'No data records found.', className = '' }) {
  // Flexible prop normalization: supports both `headers`/`rows` AND `columns`/`data`
  const tableHeaders = headers || (columns ? columns.map((c) => (typeof c === 'object' ? c.title || c.key : c)) : []);

  let tableRows = rows;
  if (!tableRows && data && columns) {
    tableRows = data.map((item) =>
      columns.map((col) => {
        const key = typeof col === 'object' ? col.key : col;
        return item[key] !== undefined ? item[key] : '-';
      })
    );
  } else if (!tableRows && data && Array.isArray(data)) {
    tableRows = data.map((item) => (Array.isArray(item) ? item : Object.values(item)));
  }

  return (
    <div className={`overflow-x-auto w-full ${className}`}>
      <table className="w-full border-collapse mt-2 text-left">
        <thead>
          <tr className="bg-slate-800/40 text-[var(--text-muted)] text-xs font-bold border-b border-[var(--border-dark)]">
            {tableHeaders.map((h, idx) => (
              <th key={idx} className="p-3">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="text-xs text-[var(--text-dark)] font-mono num-tabular">
          {tableRows && tableRows.length > 0 ? (
            tableRows.map((row, rIdx) => (
              <tr key={rIdx} className="border-b border-[var(--border-dark)] hover:bg-white/[0.02]">
                {Array.isArray(row) ? (
                  row.map((cell, cIdx) => (
                    <td key={cIdx} className="p-3">{cell}</td>
                  ))
                ) : (
                  <td className="p-3">{String(row)}</td>
                )}
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={tableHeaders.length || 1} className="p-6 text-center text-[var(--text-muted)]">
                {emptyMessage}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
