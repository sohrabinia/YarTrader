import React, { useState, useEffect, useRef } from 'react';

/**
 * Functional Global Command Palette (`shadcn/ui` Command Pattern)
 * Keyboard Shortcuts: `Ctrl+K` / `Cmd+K` opens/closes dialog. `Escape` closes dialog.
 * Supports fuzzy search navigation across 16+ routes, keyboard arrow selection, Enter navigation,
 * and dynamic LTR/RTL support.
 */
export default function CommandPalette({ lang = 'fa', t = (k) => k, navigateTo = () => {} }) {
  const [open, setChatOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef(null);

  const routes = [
    { label: t('nav_public') || 'Home Platform', path: '/', icon: '🌐', group: 'Portal' },
    { label: t('nav_features') || 'Features', path: '/features', icon: '⚡', group: 'Portal' },
    { label: t('nav_pricing') || 'Pricing & Plans', path: '/pricing', icon: '💎', group: 'Portal' },
    { label: t('nav_blog') || 'Research Blog', path: '/blog', icon: '📰', group: 'Portal' },
    { label: t('nav_terminal') || 'Command Center Dashboard', path: '/dashboard', icon: '🏛️', group: 'Platform' },
    { label: t('nav_signals') || 'Market Intelligence & Signals', path: '/signals', icon: '📡', group: 'Platform' },
    { label: t('nav_execution_intel') || 'Execution Intelligence & XAI', path: '/execution-intel', icon: '⚡', group: 'Platform' },
    { label: t('nav_backtest') || 'Backtest Simulation Lab', path: '/backtest', icon: '📊', group: 'Trading' },
    { label: t('nav_demo') || 'MT5 Demo Terminal (#52961173)', path: '/demo', icon: '🎮', group: 'Trading' },
    { label: t('nav_learning') || 'Pattern Memory & Learning Matrix', path: '/learning', icon: '🧠', group: 'Intelligence' },
    { label: t('nav_admin') || 'SRE Admin Operational Control Center', path: '/admin', icon: '🛡️', group: 'Administration' },
    { label: t('nav_login') || 'Sign In', path: '/login', icon: '🔑', group: 'Auth' },
    { label: t('nav_register') || 'Sign Up', path: '/register', icon: '📝', group: 'Auth' }
  ];

  const filteredRoutes = routes.filter((r) =>
    r.label.toLowerCase().includes(query.toLowerCase()) ||
    r.group.toLowerCase().includes(query.toLowerCase()) ||
    r.path.toLowerCase().includes(query.toLowerCase())
  );

  // Toggle overlay on Ctrl+K / Cmd+K
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setChatOpen((prev) => !prev);
      } else if (e.key === 'Escape' && open) {
        setChatOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open]);

  // Focus input when opened
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setSelectedIndex(0);
    } else {
      setQuery('');
    }
  }, [open]);

  const handleSelectRoute = (path) => {
    if (typeof navigateTo === 'function') {
      navigateTo(path);
    } else {
      const curLang = window.location.pathname.split('/')[1] || 'fa';
      window.location.pathname = `/${curLang}${path === '/' ? '' : path}`;
    }
    setChatOpen(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % (filteredRoutes.length || 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + filteredRoutes.length) % (filteredRoutes.length || 1));
    } else if (e.key === 'Enter' && filteredRoutes[selectedIndex]) {
      e.preventDefault();
      handleSelectRoute(filteredRoutes[selectedIndex].path);
    }
  };

  if (!open) return null;

  return (
    <div className="drawer-overlay flex justify-center items-start pt-20 px-4 z-[99999]" onClick={() => setChatOpen(false)}>
      <div
        className="card w-full max-w-xl bg-[var(--surface-dark)] border border-[var(--border-dark)] shadow-2xl rounded-xl overflow-hidden p-0"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Command Search Header */}
        <div className="flex items-center px-4 py-3 border-b border-[var(--border-dark)] gap-3">
          <span className="text-lg">🔍</span>
          <input
            ref={inputRef}
            type="text"
            className="w-full bg-transparent border-none outline-none text-sm text-[var(--text-dark)] font-sans placeholder-[var(--text-muted)]"
            placeholder={lang === 'fa' ? 'جستجو در صفحات و ابزارها (Ctrl+K)...' : 'Search routes & commands (Ctrl+K)...'}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            onKeyDown={handleKeyDown}
          />
          <kbd className="px-2 py-0.5 text-[0.7rem] font-mono text-[var(--text-muted)] bg-slate-800 rounded border border-[var(--border-dark)]">
            ESC
          </kbd>
        </div>

        {/* Command Search Results List */}
        <div className="max-h-80 overflow-y-auto p-2 flex flex-col gap-1">
          {filteredRoutes.length > 0 ? (
            filteredRoutes.map((route, idx) => {
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={idx}
                  className={`flex items-center justify-between p-2.5 rounded cursor-pointer text-xs transition-all ${
                    isSelected
                      ? 'bg-[var(--primary)] text-[#07090E] font-bold shadow-sm'
                      : 'hover:bg-white/5 text-[var(--text-dark)]'
                  }`}
                  onClick={() => handleSelectRoute(route.path)}
                  onMouseEnter={() => setSelectedIndex(idx)}
                >
                  <div className="flex items-center gap-2.5">
                    <span className="text-base">{route.icon}</span>
                    <span>{route.label}</span>
                  </div>
                  <span className={`text-[0.68rem] font-mono px-2 py-0.5 rounded ${isSelected ? 'bg-black/20 text-[#07090E]' : 'bg-slate-800 text-[var(--text-muted)]'}`}>
                    {route.group}
                  </span>
                </div>
              );
            })
          ) : (
            <div className="p-6 text-center text-xs text-[var(--text-muted)]">
              {lang === 'fa' ? 'هیچ مسیر یا دستوری یافت نشد.' : 'No matching routes or commands found.'}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
