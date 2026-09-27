import React from 'react';
import MetricCard from '../design-system/MetricCard';
import StatusBadge from '../design-system/StatusBadge';
import DataTable from '../design-system/DataTable';

export default function DemoView({ t, demoReport, demoTrades = [], backendState }) {
  const report = demoReport && typeof demoReport === 'object' ? demoReport : {};
  const accountId = report.account_id ?? report.account_number ?? null;
  const balance = report.balance ?? report.equity ?? null;
  const tradeRows = Array.isArray(demoTrades) ? demoTrades.filter(trade => String(trade?.symbol || '').toUpperCase() === 'XAUUSD') : [];
  const verified = Boolean(accountId);

  return (
    <div id="shell-demo" className="space-y-6">
      <div className="card" style={{ borderLeft: '4px solid var(--signal)' }}>
        <div className="flex justify-between items-center flex-wrap gap-4">
          <div><h2 className="text-xl font-bold text-[var(--signal)] mb-1">{t('demo_title')}</h2><p className="text-sm text-[var(--text-dark)]">{t('demo_desc')}</p></div>
          <StatusBadge status={backendState === 'UNREACHABLE' ? 'DATA UNAVAILABLE' : (verified ? 'DEMO VERIFIED' : 'NOT VERIFIED')} type={backendState === 'UNREACHABLE' ? 'warning' : (verified ? 'passed' : 'warning')} />
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <MetricCard title="Demo Account" value={accountId ? String(accountId) : 'DATA UNAVAILABLE'} status={verified ? 'passed' : 'warning'} subtitle={report.server || report.broker || 'DATA UNAVAILABLE'} />
        <MetricCard title="Balance / Equity" value={balance != null ? ('$' + Number(balance).toLocaleString()) : 'DATA UNAVAILABLE'} status={balance != null ? 'passed' : 'warning'} />
        <MetricCard title="Execution Verification" value={verified ? 'VERIFIED' : 'NOT VERIFIED'} status={verified ? 'passed' : 'warning'} subtitle={report.message || ''} />
        <MetricCard title="Live Trading Gate" value="HARD DISABLED" status="primary" subtitle="LIVE_TRADING_ENABLED=False" />
      </div>
      <div className="card">
        <h3 className="text-sm font-bold text-[var(--primary)] uppercase tracking-wider mb-3">Demo Trade History</h3>
        {tradeRows.length > 0 ? <DataTable columns={[{ key: 'ticket', title: 'Ticket #' }, { key: 'symbol', title: 'Symbol' }, { key: 'type', title: 'Type' }, { key: 'volume', title: 'Lots' }, { key: 'sl', title: 'Stop Loss' }, { key: 'tp', title: 'Take Profit' }, { key: 'profit', title: 'P&L ($)' }]} data={tradeRows} /> : <div className="text-sm text-[var(--text-muted)] py-6">No verified XAUUSD demo trades are available.</div>}
      </div>
    </div>
  );
}
