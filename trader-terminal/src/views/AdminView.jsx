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
        <HealthIndicator label="FastAPI Backend Services" status={devopsStatus?.status || 'DATA UNAVAILABLE'} latency={devopsStatus?.api_latency_ms != null ? String(devopsStatus.api_latency_ms) + 'ms' : undefined} />
        <HealthIndicator label="Cognitive Intelligence Pipeline" status={devopsStatus?.research_status || 'DATA UNAVAILABLE'} latency={devopsStatus?.research_latency_ms != null ? String(devopsStatus.research_latency_ms) + 'ms' : undefined} />
        <HealthIndicator label="MT5 Demo Bridge Process" status={devopsStatus?.mt5_connected == null ? 'DATA UNAVAILABLE' : (devopsStatus.mt5_connected ? 'CONNECTED' : 'DISCONNECTED')} latency={devopsStatus?.mt5_latency_ms != null ? String(devopsStatus.mt5_latency_ms) + 'ms' : undefined} />
        <HealthIndicator label="PostgreSQL & Redis Cache" status={devopsStatus?.storage_status || 'DATA UNAVAILABLE'} latency={undefined} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard title="پردازنده سیستم (CPU Usage)" value={devopsStatus?.cpu_usage_pct != null ? String(devopsStatus.cpu_usage_pct) + '%' : 'DATA UNAVAILABLE'} status={devopsStatus?.cpu_usage_pct != null ? 'passed' : 'warning'} />
        <MetricCard title="حافظه رم (RAM Usage)" value={devopsStatus?.ram_usage_pct != null ? String(devopsStatus.ram_usage_pct) + '%' : 'DATA UNAVAILABLE'} status={devopsStatus?.ram_usage_pct != null ? 'passed' : 'warning'} />
        <MetricCard title="فضای دیسک (Storage isolation)" value={devopsStatus?.disk_usage_pct != null ? String(devopsStatus.disk_usage_pct) + '%' : 'DATA UNAVAILABLE'} status={devopsStatus?.disk_usage_pct != null ? 'passed' : 'warning'} />
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
          data={Array.isArray(usersList) ? usersList : []}
        />
      </div>
    </div>
  );
}
