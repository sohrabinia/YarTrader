import React from 'react';
import MetricCard from '../design-system/MetricCard';
import StatusBadge from '../design-system/StatusBadge';
import DataTable from '../design-system/DataTable';

export default function DemoView({ t, demoReport, backendState }) {
  return (
    <div id="shell-demo" className="space-y-6">
      <div className="card" style={{ borderLeft: '4px solid var(--signal)' }}>
        <div className="flex justify-between items-center flex-wrap gap-4">
          <div>
            <h2 className="text-xl font-bold text-[var(--signal)] mb-1">🎮 مرکز اجرای آزمایشی (MT5 Demo Execution Engine)</h2>
            <p className="text-sm text-[var(--text-dark)]">
              اجرای اتونوموس سفارشات آزمایشی روی متاتریدر ۵ حساب #52961173 (Alpari-MT5-Demo) تحت ایزولاسیون کامل SRE.
            </p>
          </div>
          <StatusBadge status="DEMO ACTIVE" type="passed" />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <MetricCard title="شماره حساب آزمایشی" value="52961173" status="passed" subtitle="Alpari-MT5-Demo" />
        <MetricCard title="موجودی حساب (Balance)" value="$10,450.00" status="passed" change="+$450.00" trend="up" />
        <MetricCard title="اعتبارسنجی Session & TP" value="PASSED (>120s / Causal)" status="passed" subtitle="Pre-Entry Calendar Checked" />
        <MetricCard title="قفل ایمنی معاملات واقعی" value="HARD DISABLED" status="primary" subtitle="LIVE_TRADING_ENABLED=False" />
      </div>

      <div className="card">
        <h3 className="text-sm font-bold text-[var(--primary)] uppercase tracking-wider mb-3">تاریخچه اجرای معاملات DEMO</h3>
        <DataTable
          columns={[
            { key: 'ticket', title: 'Ticket #' },
            { key: 'symbol', title: 'Symbol' },
            { key: 'type', title: 'Type' },
            { key: 'volume', title: 'Lots' },
            { key: 'sl', title: 'Stop Loss' },
            { key: 'tp', title: 'Take Profit' },
            { key: 'profit', title: 'P&L ($)' }
          ]}
          data={[
            { ticket: '50192831', symbol: 'XAUUSD', type: 'BUY', volume: '0.10', sl: '2440.00', tp: '2475.00', profit: '+$120.00' },
            { ticket: '50192832', symbol: 'EURUSD', type: 'SELL', volume: '0.20', sl: '1.0910', tp: '1.0820', profit: '+$74.50' }
          ]}
        />
      </div>
    </div>
  );
}
