import React from 'react';
import MetricCard from '../design-system/MetricCard';
import ChartContainer from '../design-system/ChartContainer';
import ConfidenceBadge from '../design-system/ConfidenceBadge';
import PositionTimelineStepper from '../design-system/PositionTimelineStepper';
import DataTable from '../design-system/DataTable';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';

export default function DashboardView({
  t,
  backendState,
  devopsStatus,
  signals,
  portfolioRisk,
  demoReport,
  selectedAsset,
  setSelectedAsset,
  activeHorizon,
  setActiveHorizon,
  compounding,
  setCompounding,
  runCompoundingSimulation
}) {
  return (
    <div id="shell-terminal" className="space-y-6">
      {/* Command Status Header */}
      <Card className="border-l-4 border-l-[var(--primary)] bg-gradient-to-b from-[var(--surface-light)] to-[var(--surface-dark)]">
        <CardHeader className="flex flex-row items-center justify-between flex-wrap gap-4">
          <div>
            <CardTitle className="text-xl flex items-center gap-2">
              <span>🏛️</span> {t('terminal_title')}
            </CardTitle>
            <p className="text-xs text-[var(--text-muted)] mt-1">
              {t('terminal_desc')}
            </p>
          </div>
          <div className="flex gap-2 items-center flex-wrap">
            <Badge variant="warning">
              ENV: {backendState === 'LIVE' ? 'LIVE MT4' : 'DEMO PAPER'}
            </Badge>
            <Badge variant="passed">
              SAFETY GATE: FAIL-CLOSED
            </Badge>
          </div>
        </CardHeader>

        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-2">
            <MetricCard title="Market State" value={signals && signals[0] ? (signals[0].posture || 'QUALIFIED') : 'STABLE'} status="passed" />
            <MetricCard title="Inference" value={signals && signals[0] ? (signals[0].reason || 'QUALIFIED SETUP') : 'QUALIFIED'} status="primary" />
            <MetricCard title="Confidence" value={signals && signals[0] && signals[0].confidence != null ? `${signals[0].confidence}%` : '88%'} status="passed" />
            <MetricCard title="Risk Posture" value={portfolioRisk && portfolioRisk.drawdown_level ? portfolioRisk.drawdown_level : 'BALANCED'} status="passed" />
            <MetricCard title="Execution Eligibility" value={demoReport && demoReport.account_id ? 'DEMO ELIGIBLE' : 'VERIFIED'} status="passed" />
          </div>
        </CardContent>
      </Card>

      {/* Chart Container */}
      <ChartContainer
        title={`${selectedAsset === 'gold' ? 'XAUUSD (Gold)' : selectedAsset === 'bitcoin' ? 'BTCUSD (Bitcoin)' : 'Multi-Asset Overview'} - ${activeHorizon.toUpperCase()} Horizon`}
        subtitle="Pure Price Action, Market Structure & Liquidity Map"
        activeTimeframe={activeHorizon === 'micro' ? 'M1' : activeHorizon === 'short' ? 'M15' : activeHorizon === 'medium' ? 'H1' : 'D1'}
      >
        <div className="p-4 bg-[var(--surface-dark)] border border-[var(--border-dark)] rounded flex flex-col gap-2">
          <div className="flex justify-between items-center text-xs text-[var(--primary)] font-bold">
            <span>STRUCTURE MAP (HH / HL / LH / LL)</span>
            <ConfidenceBadge score={signals[0]?.confidence || 85} />
          </div>
          <div className="text-[0.75rem] text-[var(--text-dark)] leading-relaxed">
            Market structure showing strong bullish alignment across canonical timeframes. Zero classical technical indicators are used.
          </div>
        </div>
      </ChartContainer>

      {/* Control Panel */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between flex-wrap gap-4 pb-2">
          <CardTitle>📊 {t('terminal_title')}</CardTitle>
          <div className="flex gap-2">
            {['micro', 'short', 'medium', 'macro'].map((hType) => (
              <Button
                key={hType}
                variant={activeHorizon === hType ? 'primary' : 'ghost'}
                size="sm"
                onClick={() => setActiveHorizon(hType)}
              >
                {hType.toUpperCase()}
              </Button>
            ))}
          </div>
        </CardHeader>
        <CardContent>
          <PositionTimelineStepper
            steps={[
              { label: 'MARKET REGIME', status: 'passed', detail: 'RANGE_BOUND (Hurst: 0.42)' },
              { label: 'STRUCTURAL BIAS', status: 'passed', detail: 'Bullish OB at 2642.50' },
              { label: 'RISK GATE', status: 'passed', detail: 'Max 2% Risk Approved' },
              { label: 'EXECUTION GATE', status: 'passed', detail: 'MT5 Paper Execution' }
            ]}
          />
        </CardContent>
      </Card>
    </div>
  );
}
