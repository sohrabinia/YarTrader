import React from 'react';

export function AppShell({ header, sidebar, children, chatbot }) {
  return (
    <div className="min-h-screen bg-[var(--surface-dark)] text-[var(--text-dark)] font-sans flex flex-col">
      {header}
      <div className="flex flex-1 w-full max-w-7xl mx-auto px-4 py-6 gap-6">
        {sidebar && (
          <aside className="w-64 flex-shrink-0 hidden md:block">
            {sidebar}
          </aside>
        )}
        <main className="flex-1 min-w-0">
          {children}
        </main>
      </div>
      {chatbot}
    </div>
  );
}

export function PageHeader({ title, subtitle, badge }) {
  return (
    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6 pb-4 border-b border-[var(--border-dark)]">
      <div>
        <h1 className="text-2xl font-bold text-[var(--primary)] tracking-tight flex items-center gap-3">
          {title}
        </h1>
        {subtitle && (
          <p className="text-sm text-[var(--text-muted)] mt-1">
            {subtitle}
          </p>
        )}
      </div>
      {badge && <div className="flex items-center gap-2">{badge}</div>}
    </div>
  );
}
