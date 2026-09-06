import React from 'react';
import MetricCard from '../design-system/MetricCard';
import HealthIndicator from '../design-system/HealthIndicator';
import DataTable from '../design-system/DataTable';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';

export default function AdminView({ t, devopsStatus, systemMetrics, usersList }) {
  return (
    <div id="shell-admin" className="space-y-6">
      <Card className="border-l-4 border-l-[var(--danger)]">
        <CardHeader>
          <CardTitle className="text-xl text-[var(--danger)]">
            🛡️ YarTrader SRE Command & Control Center
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-[var(--text-muted)]">
            Infrastructure telemetry, RBAC permissions control, AI engine health, and platform safety gates.
          </p>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <HealthIndicator label="FastAPI Backend Services" status="HEALTHY" latency="14ms" />
        <HealthIndicator label="Cognitive Intelligence Pipeline" status="HEALTHY" latency="8ms" />
        <HealthIndicator label="MT5 Demo Bridge Process" status="HEALTHY" latency="22ms" />
        <HealthIndicator label="PostgreSQL & Redis Cache" status="HEALTHY" latency="5ms" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard title="CPU Usage" value="14.2%" status="passed" subtitle="4 Cores Active" />
        <MetricCard title="RAM Allocation" value="2.8 GB / 16 GB" status="passed" subtitle="17.5% Allocation" />
        <MetricCard title="System Health Score" value="99.8%" status="passed" subtitle="SRE Target Satisfied" />
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>👥 Registered Platform Users</CardTitle>
          <Badge variant="primary">ADMIN RBAC ACTIVE</Badge>
        </CardHeader>
        <CardContent>
          <DataTable
            headers={['User ID', 'Name', 'Email', 'Role', 'Status', 'Actions']}
            rows={[
              ['usr-admin-01', <strong>SRE Administrator</strong>, 'admin@yartrader.app', <Badge variant="warning">ADMIN</Badge>, <Badge variant="passed">ACTIVE</Badge>, <Button variant="ghost" size="sm">Manage</Button>],
              ['usr-trader-02', <strong>Elite Trader</strong>, 'trader@yartrader.app', <Badge variant="neutral">USER</Badge>, <Badge variant="passed">ACTIVE</Badge>, <Button variant="ghost" size="sm">Inspect</Button>]
            ]}
          />
        </CardContent>
      </Card>
    </div>
  );
}
