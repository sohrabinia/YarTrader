import React from 'react';
import MetricCard from '../design-system/MetricCard';
import HealthIndicator from '../design-system/HealthIndicator';
import DataTable from '../design-system/DataTable';

export default function AdminView({ t, devopsStatus, systemMetrics, usersList }) {
  return (
    <div id="shell-admin" className="space-y-6">
      <div className="card" style={{ borderLeft: '4px solid #ef4444' }}>
        <h2 className="text-xl font-bold text-red-500 mb-1">🛡️ پنل کنترل و پایش فرماندهی SRE Admin</h2>
        <p className="text-sm text-[var(--text-dark)]">
          پایش زیرساخت، کنترل دسترسی‌های RBAC، تلمتری موتورهای هوش مصنوعی و کلیدهای ایمنی پلتفرم.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <HealthIndicator label="FastAPI Backend Services" status="HEALTHY" latency="14ms" />
        <HealthIndicator label="Predictive Shadow Engine" status="HEALTHY" latency="8ms" />
        <HealthIndicator label="MT5 Demo Bridge Process" status="HEALTHY" latency="22ms" />
        <HealthIndicator label="PostgreSQL & Redis Cache" status="HEALTHY" latency="5ms" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard title="پردازنده سیستم (CPU Usage)" value="14.2%" status="passed" subtitle="4 Cores Active" />
        <MetricCard title="حافظه رم (RAM Usage)" value="2.8 GB / 16 GB" status="passed" subtitle="17.5% Allocation" />
        <MetricCard title="فضای دیسک (Storage isolation)" value="12.4 GB / 250 GB" status="passed" subtitle="YarTraderStorageRoot" />
      </div>

      <div className="card">
        <h3 className="text-sm font-bold text-[var(--primary)] uppercase tracking-wider mb-3">مدیریت کاربران و دسترسی‌های RBAC</h3>
        <DataTable
          columns={[
            { key: 'user', title: 'کاربر' },
            { key: 'email', title: 'ایمیل' },
            { key: 'role', title: 'نقش دسترسی (RBAC)' },
            { key: 'status', title: 'وضعیت حساب' }
          ]}
          data={[
            { user: 'مدیر ارشد (Owner)', email: 'admin@yartrader.internal', role: 'ADMIN', status: 'ACTIVE' },
            { user: 'اپراتور سیستم', email: 'operator@yartrader.internal', role: 'OPERATOR', status: 'ACTIVE' },
            { user: 'تحلیل‌گر ارشد', email: 'analyst@yartrader.internal', role: 'ANALYST', status: 'ACTIVE' }
          ]}
        />
      </div>
    </div>
  );
}
