import React from 'react';

/**
 * Institutional Chart Container Abstraction
 * Supports financial title, timeframe toolbar, loading skeleton, empty state, error boundary,
 * responsive canvas container, dark institutional styling, and tabular numeric formatting.
 */
export default function ChartContainer({
  title,
  subtitle,
  children,
  loading = false,
  empty = false,
  error = null,
  activeTimeframe = 'H1',
  onTimeframeChange,
  timeframes = ['M1', 'M5', 'M15', 'H1', 'H4', 'D1', 'W1'],
  className = ''
}) {
  return (
    <div className={`card border border-[var(--border-dark)] bg-[var(--surface-dark)] p-5 rounded-lg shadow-md ${className}`}>
      {/* Chart Header Toolbar */}
      <div className="flex justify-between items-center flex-wrap gap-3 mb-4 pb-3 border-b border-[var(--border-dark)]">
        <div>
          {title && <h3 className="m-0 text-[var(--primary)] font-bold text-lg">{title}</h3>}
          {subtitle && <p className="m-0 mt-1 text-xs text-[var(--text-muted)]">{subtitle}</p>}
        </div>

        {/* Timeframe Selector Area */}
        {timeframes && timeframes.length > 0 && (
          <div className="flex gap-1.5 bg-slate-900/60 p-1 rounded border border-[var(--border-dark)]">
            {timeframes.map((tf) => (
              <button
                key={tf}
                type="button"
                className={`px-2.5 py-1 text-xs font-mono font-bold rounded transition-all ${
                  activeTimeframe === tf
                    ? 'bg-[var(--primary)] text-[#07090E] shadow-sm'
                    : 'text-[var(--text-muted)] hover:text-white hover:bg-white/5'
                }`}
                onClick={() => onTimeframeChange && onTimeframeChange(tf)}
              >
                {tf}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Chart Canvas Content Area */}
      <div className="relative min-h-[320px] w-full flex flex-col justify-center items-center">
        {loading ? (
          <div className="flex flex-col items-center gap-3 text-[var(--primary)]">
            <div className="w-8 h-8 border-3 border-[var(--primary)] border-t-transparent rounded-full animate-spin"></div>
            <span className="text-xs font-semibold">Loading Market Structure Data...</span>
          </div>
        ) : error ? (
          <div className="p-4 bg-red-500/10 border border-[var(--danger)] text-[var(--danger)] text-sm rounded text-center max-w-md">
            ⚠️ {error.message || String(error)}
          </div>
        ) : empty ? (
          <div className="text-center text-[var(--text-muted)] p-8">
            <div className="text-3xl mb-2">📊</div>
            <div className="font-bold text-sm text-[var(--text-dark)] mb-1">No Chart Data Available</div>
            <p className="text-xs">Market data stream is currently offline for this symbol/timeframe.</p>
          </div>
        ) : (
          <div className="w-full h-full font-mono text-xs num-tabular">
            {children}
          </div>
        )}
      </div>
    </div>
  );
}
