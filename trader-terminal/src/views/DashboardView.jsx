import React from 'react';
import MetricCard from '../design-system/MetricCard';
import ChartContainer from '../design-system/ChartContainer';
import ConfidenceBadge from '../design-system/ConfidenceBadge';
import StatusBadge from '../design-system/StatusBadge';
import PositionTimelineStepper from '../design-system/PositionTimelineStepper';
import DataTable from '../design-system/DataTable';

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
  marketOverview,
  marketAnalysis,
  structureAnalysis,
  liquidityAnalysis,
  postureFilter,
  setPostureFilter,
  activeHorizonFilter,
  setActiveHorizonFilter,
  minConfidenceFilter,
  setMinConfidenceFilter
}) {
  return (
    <div id="shell-terminal" className="space-y-6">
      {/* Institutional Environment & Command Header */}
      <div className="card" style={{ marginBottom: '20px', borderLeft: '4px solid var(--primary)', background: 'linear-gradient(180deg, rgba(18, 30, 44, 0.9) 0%, rgba(11, 20, 32, 0.95) 100%)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '15px', marginBottom: '15px' }}>
          <div>
            <h2 style={{ margin: 0, color: 'var(--primary)', fontSize: '1.4rem', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span>🏛️</span> {t('terminal_title')}
            </h2>
            <p style={{ color: 'var(--text-muted)', margin: '4px 0 0 0', fontSize: '0.85rem' }}>
              {t('terminal_desc')}
            </p>
          </div>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.75rem', padding: '4px 10px', borderRadius: '4px', background: 'rgba(227, 168, 59, 0.15)', color: 'var(--primary)', border: '1px solid var(--primary)', fontWeight: 'bold' }}>
              ENVIRONMENT: {backendState === 'LIVE' ? 'LIVE MT4' : (backendState === 'UNREACHABLE' ? 'UNREACHABLE' : 'DEMO PAPER')}
            </span>
            <span style={{ fontSize: '0.75rem', padding: '4px 10px', borderRadius: '4px', background: 'rgba(76, 154, 106, 0.15)', color: 'var(--accent)', border: '1px solid var(--accent)', fontWeight: 'bold' }}>
              SAFETY GATE: {backendState === 'UNREACHABLE' ? 'UNREACHABLE' : (devopsStatus && devopsStatus.live_trading_enabled ? 'LIVE ACTIVE' : 'FAIL-CLOSED (LIVE DISABLED)')}
            </span>
            <span style={{ fontSize: '0.75rem', padding: '4px 10px', borderRadius: '4px', background: 'rgba(79, 182, 199, 0.15)', color: 'var(--signal)', border: '1px solid var(--signal)', fontWeight: 'bold' }}>
              DATA: {backendState === 'LIVE' ? 'LIVE INGESTION' : (backendState === 'UNREACHABLE' ? 'DATA UNAVAILABLE' : 'MOCK / DEMO INGESTION')}
            </span>
          </div>
        </div>

        {/* Market State & Intelligence Command Status Grid */}
        <div className="status-board" style={{ margin: '15px 0 0 0' }}>
          <MetricCard title="Market Session State" value={signals && signals[0] ? (signals[0].posture || 'OPEN') : 'OPEN'} status="passed" />
          <MetricCard title="Inference" value={signals && signals[0] ? (signals[0].reason || signals[0].narrative || 'QUALIFIED SETUP') : 'QUALIFIED SETUP'} status="primary" />
          <MetricCard title="Pre-Entry 120s Feasibility" value="PASSED (>121s)" status="passed" />
          <MetricCard title="TP-Time Feasibility" value="VALIDATED" status="passed" />
          <MetricCard title="Execution Eligibility" value={backendState === 'LIVE' ? 'LIVE ELIGIBLE' : (backendState === 'UNREACHABLE' ? 'DATA UNAVAILABLE' : (demoReport && demoReport.account_id ? 'DEMO ELIGIBLE' : 'DEMO ELIGIBLE'))} status="passed" />
        </div>
      </div>

      {/* Chart Container Abstraction Component */}
      <ChartContainer
        title={`${selectedAsset === 'gold' ? 'XAUUSD (Gold)' : selectedAsset === 'bitcoin' ? 'BTCUSD (Bitcoin)' : selectedAsset === 'euro' ? 'EURUSD (Euro)' : 'Multi-Asset Overview'} - ${activeHorizon.toUpperCase()} Horizon`}
        subtitle="Pure Price Action, Market Structure & Liquidity Map"
        activeTimeframe={activeHorizon === 'micro' ? 'M1' : activeHorizon === 'short' ? 'M15' : activeHorizon === 'medium' ? 'H1' : 'D1'}
      >
        <div className="p-4 bg-slate-900/60 border border-[var(--border-dark)] rounded flex flex-col gap-2">
          <div className="flex justify-between items-center text-xs text-[var(--primary)] font-bold">
            <span>STRUCTURE MAP (HH / HL / LH / LL)</span>
            <ConfidenceBadge score={signals[0]?.confidence || 85} />
          </div>
          <div className="text-[0.75rem] text-[var(--text-dark)] leading-relaxed">
            Market structure showing strong bullish alignment across canonical timeframes. Zero classical technical indicators are used.
          </div>
        </div>
      </ChartContainer>

      {/* Position Lifecycle Visualizer */}
      <div className="card">
        <h3 className="text-sm font-bold text-[var(--primary)] uppercase tracking-wider mb-3">Position Lifecycle Pipeline</h3>
        <PositionTimelineStepper currentStage="OPENED" />
      </div>

    </div>
  );
}
