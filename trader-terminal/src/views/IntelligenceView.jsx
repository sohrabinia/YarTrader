import React, { useState } from 'react';
import MetricCard from '../design-system/MetricCard';
import StatusBadge from '../design-system/StatusBadge';
import ConfidenceBadge from '../design-system/ConfidenceBadge';
import DataTable from '../design-system/DataTable';

export default function IntelligenceView({ t, lang = 'fa' }) {
  // State for Filters
  const [selectedSymbol, setSelectedSymbol] = useState('XAUUSD');
  const [selectedTimeframe, setSelectedTimeframe] = useState('H1');
  const [selectedStructure, setSelectedStructure] = useState('all');
  const [selectedDirection, setSelectedDirection] = useState('all');
  const [selectedPhase, setSelectedPhase] = useState('all');
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [selectedConfidence, setSelectedConfidence] = useState('all');

  // Active Scale Drilldown State
  const [activeDrilldownScale, setActiveDrilldownScale] = useState('H1');

  // Canonical Historical Cases (50 cases sample summary)
  const historicalCases = [
    { id: 'FC-101', date: '2024-11-12 14:00', symbol: 'XAUUSD', timeframe: 'H1', base: 'Bullish Base (Range $2,610-$2,625)', internal: 'Accumulation (4 Rotations, Compression)', legSeq: 'Leg 1 → Return 38.2% → Leg 2', targetZone: '$2,655 - $2,670', status: 'Validated', result: 'Reached Target ($2,668)', failureCause: '-' },
    { id: 'FC-102', date: '2024-11-18 09:00', symbol: 'XAUUSD', timeframe: 'M15', base: 'Neutral Base (Range $2,640-$2,648)', internal: 'Balanced (Expansion Attempt Failed)', legSeq: 'Leg 1 Breakdown', targetZone: '$2,620 - $2,628', status: 'Failed', result: 'Bearish Breakdown', failureCause: 'Daily Higher Timeframe Bullish Alignment Conflict' },
    { id: 'FC-103', date: '2024-12-02 16:30', symbol: 'XAUUSD', timeframe: 'H4', base: 'Bullish Base (Range $2,680-$2,705)', internal: 'Expansion Preparation (HH + HL)', legSeq: 'Leg 1 → Leg 2 → Exhaustion', targetZone: '$2,740 - $2,755', status: 'Validated', result: 'Extended to $2,762', failureCause: '-' },
    { id: 'FC-104', date: '2024-12-15 11:00', symbol: 'XAUUSD', timeframe: 'Daily', base: 'Bearish Base (Range $2,720-$2,750)', internal: 'Distribution (Lower Highs)', legSeq: 'Leg 1 → Return → Leg 2', targetZone: '$2,650 - $2,670', status: 'Validated', result: 'Reached Target ($2,652)', failureCause: '-' },
    { id: 'FC-105', date: '2025-01-08 08:00', symbol: 'XAUUSD', timeframe: 'M5', base: 'Neutral Base (Range $2,660-$2,665)', internal: 'High Volatility Rotations', legSeq: 'Leg 1 Fakeout → Return', targetZone: '$2,675 - $2,680', status: 'Failed', result: 'Stopped Out at 120s Floor', failureCause: 'Micro Noisy Structure / M5 Breakout Failure' },
    { id: 'FC-106', date: '2025-01-20 15:15', symbol: 'XAUUSD', timeframe: 'H1', base: 'Bullish Base (Range $2,695-$2,710)', internal: 'Accumulation-like', legSeq: 'Leg 1 → Return → Leg 2 → Leg 3', targetZone: '$2,750 - $2,765', status: 'Validated', result: 'Reached Target ($2,758)', failureCause: '-' }
  ];

  return (
    <div id="shell-intel" className="space-y-6">
      {/* Primary Status Area & Scientific Release Gate Header */}
      <div className="card" style={{ borderLeft: '6px solid var(--danger)', backgroundColor: 'rgba(194, 74, 62, 0.05)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '15px' }}>
          <div>
            <h2 className="text-xl font-bold text-[var(--primary)] mb-1" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span>💠</span> YarTrader Autonomous Fractal Intelligence
            </h2>
            <p className="text-sm text-[var(--text-dark)] leading-relaxed">
              XAUUSD Multi-Timeframe Fractal Discovery, Validation & Scientific Release Status
            </p>
          </div>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.75rem', padding: '4px 10px', borderRadius: '4px', background: 'rgba(76, 154, 106, 0.2)', color: 'var(--accent)', border: '1px solid var(--accent)', fontWeight: 'bold' }}>
              SCIENTIFIC VALIDATION: PASS
            </span>
            <span style={{ fontSize: '0.75rem', padding: '4px 10px', borderRadius: '4px', background: 'rgba(76, 154, 106, 0.2)', color: 'var(--accent)', border: '1px solid var(--accent)', fontWeight: 'bold' }}>
              ENGINEERING IMPLEMENTATION: PASS
            </span>
            <span style={{ fontSize: '0.75rem', padding: '4px 10px', borderRadius: '4px', background: 'rgba(76, 154, 106, 0.2)', color: 'var(--accent)', border: '1px solid var(--accent)', fontWeight: 'bold' }}>
              SAFETY & LIFECYCLE: PASS
            </span>
            <span style={{ fontSize: '0.75rem', padding: '4px 10px', borderRadius: '4px', background: 'rgba(194, 74, 62, 0.2)', color: 'var(--danger)', border: '1px solid var(--danger)', fontWeight: 'bold' }}>
              PROFITABILITY: NOT ESTABLISHED / FAIL
            </span>
            <span style={{ fontSize: '0.75rem', padding: '4px 10px', borderRadius: '4px', background: 'rgba(227, 168, 59, 0.2)', color: 'var(--primary)', border: '1px solid var(--primary)', fontWeight: 'bold' }}>
              RELEASE STATUS: NOT READY
            </span>
            <span style={{ fontSize: '0.75rem', padding: '4px 10px', borderRadius: '4px', background: 'rgba(194, 74, 62, 0.2)', color: 'var(--danger)', border: '1px solid var(--danger)', fontWeight: 'bold' }}>
              LIVE TRADING: DISABLED (REAL_ORDERS = 0)
            </span>
          </div>
        </div>

        {/* Status Verification Board */}
        <div style={{ marginTop: '20px', padding: '15px', background: 'rgba(11, 20, 32, 0.8)', borderRadius: '6px', border: '1px solid var(--border-dark)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px', textAlign: 'center' }}>
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>IMPLEMENTATION</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: 'var(--accent)' }}>PASS</div>
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>SCIENTIFIC VALIDATION</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: 'var(--accent)' }}>PASS</div>
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>SESSION SAFETY</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: 'var(--accent)' }}>PASS</div>
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>POSITION LIFECYCLE</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: 'var(--accent)' }}>PASS</div>
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>PROFITABILITY</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: 'var(--danger)' }}>FAIL</div>
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>RELEASE READY</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: 'var(--primary)' }}>NO</div>
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>LIVE TRADING</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: 'var(--danger)' }}>DISABLED</div>
            </div>
          </div>
        </div>
      </div>

      {/* Profitability Warning Banner */}
      <div className="card" style={{ borderLeft: '6px solid var(--danger)', backgroundColor: 'rgba(194, 74, 62, 0.1)' }}>
        <h3 className="text-md font-bold text-[var(--danger)] uppercase tracking-wider mb-2" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>⚠️</span> Profitability Failure Warning
        </h3>
        <p className="text-sm font-semibold text-[var(--text-light)] mb-2">
          "Profitability has not yet been established."
        </p>
        <p className="text-xs text-[var(--text-dark)] leading-relaxed mb-4">
          The current research demonstrates substantial improvements in lifecycle safety, risk control, and structural filtering, but the validated strategy does not yet demonstrate positive expectancy.
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '4px', border: '1px solid var(--danger)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>EXPECTANCY</div>
            <div dir="ltr" style={{ fontSize: '1.1rem', fontWeight: 'bold', color: 'var(--danger)' }}>-$4.60 / trade</div>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '4px', border: '1px solid var(--danger)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>PROFIT FACTOR</div>
            <div dir="ltr" style={{ fontSize: '1.1rem', fontWeight: 'bold', color: 'var(--danger)' }}>0.86</div>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '4px', border: '1px solid var(--danger)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>NET P&L</div>
            <div dir="ltr" style={{ fontSize: '1.1rem', fontWeight: 'bold', color: 'var(--danger)' }}>-$2,066.52</div>
          </div>
        </div>
      </div>

      {/* Canonical Validation Metrics Grid */}
      <div className="card">
        <h3 className="text-sm font-bold text-[var(--primary)] uppercase tracking-wider mb-3">
          📊 Verified Research & Lifecycle Metrics
        </h3>
        <div className="status-board">
          <MetricCard title="Opportunities (N)" value="500 Evaluated" status="neutral" />
          <MetricCard title="Accepted / Rejected" value="449 / 51" status="passed" />
          <MetricCard title="Autonomous Win Rate" value="30.73%" status="failed" />
          <MetricCard title="Expectancy" value="-$4.60 / trade" status="failed" />
          <MetricCard title="Profit Factor" value="0.86" status="failed" />
          <MetricCard title="Net P&L" value="-$2,066.52" status="failed" />
          <MetricCard title="Average MAE / MFE" value="5.07 / 5.42" status="passed" />
          <MetricCard title="Avg Holding Time" value="417.9 M1 bars" status="neutral" />
          <MetricCard title="Min Hold Floor" value="120s Floor Guard" status="passed" />
          <MetricCard title="Holding Floor Exits (<120s)" value="0 Violations" status="passed" />
          <MetricCard title="Session Cutoff Violations" value="0 Violations" status="passed" />
          <MetricCard title="Overnight Open Positions" value="0 Positions" status="passed" />
          <MetricCard title="Macro Aligned / Neutral / CT" value="281 / 112 / 56" status="neutral" />
          <MetricCard title="Research Test Suite" value="45/45 PASS" status="passed" />
          <MetricCard title="Artifact Drift" value="0 Drift" status="passed" />
        </div>
      </div>

      {/* Historical Research Comparison Section */}
      <div className="card">
        <h3 className="text-sm font-bold text-[var(--primary)] uppercase tracking-wider mb-2">
          📈 HISTORICAL RESEARCH COMPARISON
        </h3>
        <p className="text-xs text-[var(--text-dark)] mb-4">
          Direct comparative evaluation between unconstrained baseline and autonomous position lifecycle intelligence.
        </p>

        <DataTable
          headers={['Metric', 'BASELINE (Unconstrained)', 'AUTONOMOUS (Lifecycle & Safety Enforced)', 'Net Improvement']}
          rows={[
            ['Win Rate', '22.20%', '30.73%', <span style={{ color: 'var(--accent)', fontWeight: 'bold' }}>+8.53%</span>],
            ['Expectancy', '-$7.90 / trade', '-$4.60 / trade', <span style={{ color: 'var(--accent)', fontWeight: 'bold' }}>+$3.30 / trade</span>],
            ['Profit Factor', '0.81', '0.86', <span style={{ color: 'var(--accent)', fontWeight: 'bold' }}>+0.05</span>],
            ['Net P&L', '-$3,950.00', '-$2,066.52', <span style={{ color: 'var(--accent)', fontWeight: 'bold' }}>+$1,883.48</span>]
          ]}
        />
      </div>

      {/* Verified Capabilities Checklist */}
      <div className="card">
        <h3 className="text-sm font-bold text-[var(--accent)] uppercase tracking-wider mb-3">
          ✅ Verified System Capabilities (Engineering & Safety)
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '10px', fontSize: '0.85rem' }}>
          <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '10px 14px', borderRadius: '4px', border: '1px solid var(--border-dark)', color: 'var(--text-light)' }}>
            <span style={{ color: 'var(--accent)', fontWeight: 'bold' }}>✓</span> Multi-Timeframe Fractal Intelligence
          </div>
          <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '10px 14px', borderRadius: '4px', border: '1px solid var(--border-dark)', color: 'var(--text-light)' }}>
            <span style={{ color: 'var(--accent)', fontWeight: 'bold' }}>✓</span> H4/D1 Macro Trend Filtering
          </div>
          <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '10px 14px', borderRadius: '4px', border: '1px solid var(--border-dark)', color: 'var(--text-light)' }}>
            <span style={{ color: 'var(--accent)', fontWeight: 'bold' }}>✓</span> M5/M15 Noise Arbitration
          </div>
          <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '10px 14px', borderRadius: '4px', border: '1px solid var(--border-dark)', color: 'var(--text-light)' }}>
            <span style={{ color: 'var(--accent)', fontWeight: 'bold' }}>✓</span> Position Lifecycle Protection
          </div>
          <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '10px 14px', borderRadius: '4px', border: '1px solid var(--border-dark)', color: 'var(--text-light)' }}>
            <span style={{ color: 'var(--accent)', fontWeight: 'bold' }}>✓</span> 120-Second Minimum Normal Lifetime
          </div>
          <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '10px 14px', borderRadius: '4px', border: '1px solid var(--border-dark)', color: 'var(--text-light)' }}>
            <span style={{ color: 'var(--accent)', fontWeight: 'bold' }}>✓</span> Session-Aware Entry Protection
          </div>
          <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '10px 14px', borderRadius: '4px', border: '1px solid var(--border-dark)', color: 'var(--text-light)' }}>
            <span style={{ color: 'var(--accent)', fontWeight: 'bold' }}>✓</span> Session-Flat Protection
          </div>
          <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '10px 14px', borderRadius: '4px', border: '1px solid var(--border-dark)', color: 'var(--text-light)' }}>
            <span style={{ color: 'var(--accent)', fontWeight: 'bold' }}>✓</span> Risk-Budget Position Sizing
          </div>
          <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '10px 14px', borderRadius: '4px', border: '1px solid var(--border-dark)', color: 'var(--text-light)' }}>
            <span style={{ color: 'var(--accent)', fontWeight: 'bold' }}>✓</span> Lookahead Protection
          </div>
          <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '10px 14px', borderRadius: '4px', border: '1px solid var(--border-dark)', color: 'var(--text-light)' }}>
            <span style={{ color: 'var(--accent)', fontWeight: 'bold' }}>✓</span> OOS Validation
          </div>
          <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '10px 14px', borderRadius: '4px', border: '1px solid var(--border-dark)', color: 'var(--text-light)' }}>
            <span style={{ color: 'var(--accent)', fontWeight: 'bold' }}>✓</span> Walk-Forward Validation
          </div>
          <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '10px 14px', borderRadius: '4px', border: '1px solid var(--border-dark)', color: 'var(--text-light)' }}>
            <span style={{ color: 'var(--accent)', fontWeight: 'bold' }}>✓</span> Artifact Reconciliation
          </div>
        </div>
      </div>

      {/* Research Dataset Status Section */}
      <div className="card">
        <h3 className="text-sm font-bold text-[var(--primary)] uppercase tracking-wider mb-3">
          🔬 Research Dataset & Environment Context
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px', fontSize: '0.85rem' }}>
          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '4px', border: '1px solid var(--border-dark)' }}>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Dataset</div>
            <div style={{ fontWeight: 'bold', color: 'var(--primary)' }}>XAUUSD M1 Dukascopy</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-dark)' }}>2021–2026 (5 Years)</div>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '4px', border: '1px solid var(--border-dark)' }}>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>M1 Bars</div>
            <div style={{ fontWeight: 'bold', color: 'var(--primary)' }}>2,460,951</div>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '4px', border: '1px solid var(--border-dark)' }}>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Opportunities</div>
            <div style={{ fontWeight: 'bold', color: 'var(--primary)' }}>500 Paired</div>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '4px', border: '1px solid var(--border-dark)' }}>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Research Tests</div>
            <div style={{ fontWeight: 'bold', color: 'var(--accent)' }}>45/45 PASS</div>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '4px', border: '1px solid var(--border-dark)' }}>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Artifact Drift</div>
            <div style={{ fontWeight: 'bold', color: 'var(--accent)' }}>0</div>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '4px', border: '1px solid var(--border-dark)' }}>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Live Orders</div>
            <div style={{ fontWeight: 'bold', color: 'var(--accent)' }}>0</div>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '4px', border: '1px solid var(--border-dark)' }}>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Live Trading</div>
            <div style={{ fontWeight: 'bold', color: 'var(--danger)' }}>DISABLED</div>
          </div>
        </div>
      </div>

      {/* Filter Control Bar */}
      <div className="card" style={{ borderTop: '4px solid var(--primary)' }}>
        <h3 className="text-sm font-bold text-[var(--primary)] uppercase tracking-wider mb-3">
          🔍 Master Fractal Intelligence Filters
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '12px', alignItems: 'center' }}>
          <div>
            <label className="form-label" style={{ fontSize: '0.75rem' }}>Symbol</label>
            <select className="select-field" style={{ width: '100%', padding: '6px' }} value={selectedSymbol} onChange={e => setSelectedSymbol(e.target.value)}>
              <option value="XAUUSD">XAUUSD (Gold)</option>
            </select>
          </div>

          <div>
            <label className="form-label" style={{ fontSize: '0.75rem' }}>Timeframe</label>
            <select className="select-field" style={{ width: '100%', padding: '6px' }} value={selectedTimeframe} onChange={e => setSelectedTimeframe(e.target.value)}>
              <option value="Monthly">Monthly</option>
              <option value="Weekly">Weekly</option>
              <option value="Daily">Daily</option>
              <option value="H4">H4</option>
              <option value="H1">H1</option>
              <option value="M15">M15</option>
              <option value="M5">M5</option>
            </select>
          </div>

          <div>
            <label className="form-label" style={{ fontSize: '0.75rem' }}>Structure Type</label>
            <select className="select-field" style={{ width: '100%', padding: '6px' }} value={selectedStructure} onChange={e => setSelectedStructure(e.target.value)}>
              <option value="all">All Structures</option>
              <option value="Base">Base Formation</option>
              <option value="Expansion">Expansion</option>
              <option value="Leg">Leg Sequence</option>
              <option value="Return">Return Depth</option>
              <option value="New Base">New Base</option>
            </select>
          </div>

          <div>
            <label className="form-label" style={{ fontSize: '0.75rem' }}>Direction</label>
            <select className="select-field" style={{ width: '100%', padding: '6px' }} value={selectedDirection} onChange={e => setSelectedDirection(e.target.value)}>
              <option value="all">All Directions</option>
              <option value="Bullish">Bullish</option>
              <option value="Bearish">Bearish</option>
              <option value="Neutral">Neutral</option>
            </select>
          </div>

          <div>
            <label className="form-label" style={{ fontSize: '0.75rem' }}>Phase</label>
            <select className="select-field" style={{ width: '100%', padding: '6px' }} value={selectedPhase} onChange={e => setSelectedPhase(e.target.value)}>
              <option value="all">All Phases</option>
              <option value="Building Base">Building Base</option>
              <option value="Expansion Preparation">Expansion Prep</option>
              <option value="Expansion">Expansion</option>
              <option value="Return">Return</option>
              <option value="Completed">Completed</option>
            </select>
          </div>

          <div>
            <label className="form-label" style={{ fontSize: '0.75rem' }}>Status</label>
            <select className="select-field" style={{ width: '100%', padding: '6px' }} value={selectedStatus} onChange={e => setSelectedStatus(e.target.value)}>
              <option value="all">All Statuses</option>
              <option value="Active">Active Live</option>
              <option value="Historical">Historical Replay</option>
              <option value="Validated">Validated</option>
              <option value="Failed">Failed</option>
            </select>
          </div>

          <div>
            <label className="form-label" style={{ fontSize: '0.75rem' }}>Confidence</label>
            <select className="select-field" style={{ width: '100%', padding: '6px' }} value={selectedConfidence} onChange={e => setSelectedConfidence(e.target.value)}>
              <option value="all">All Confidence</option>
              <option value="0-50">0 - 50%</option>
              <option value="50-70">50 - 70%</option>
              <option value="70-90">70 - 90%</option>
              <option value="90+">90%+ </option>
            </select>
          </div>
        </div>
      </div>

      {/* Multi-Timeframe Nested Scale Explorer */}
      <div className="card">
        <h3 className="text-sm font-bold text-[var(--primary)] uppercase tracking-wider mb-3">
          🌐 Multi-Timeframe Fractal Scale Explorer & Active Hierarchy
        </h3>
        <p className="text-xs text-[var(--text-dark)] mb-4">
          Click any timeframe scale to inspect controlling market structure, internal noise status, and nested Base boundaries.
        </p>

        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '20px' }}>
          {['Monthly', 'Weekly', 'Daily', 'H4', 'H1', 'M15', 'M5'].map(scale => (
            <button
              key={scale}
              className={`btn ${activeDrilldownScale === scale ? '' : 'btn-secondary'}`}
              style={{ padding: '8px 16px', fontSize: '0.85rem' }}
              onClick={() => setActiveDrilldownScale(scale)}
            >
              {scale === 'H1' ? `⭐ ${scale} (Dominant Active)` : scale}
            </button>
          ))}
        </div>

        {/* Drilldown Inspector Card */}
        <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '20px', borderRadius: '8px', border: '1px solid var(--border-dark)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
            <h4 style={{ margin: 0, color: 'var(--primary)' }}>
              Scale Context: {activeDrilldownScale} {activeDrilldownScale === 'H1' ? '(DOMINANT CONTROLLING SCALE)' : ''}
            </h4>
            <StatusBadge status={activeDrilldownScale === 'M5' ? 'warning' : 'passed'} label={activeDrilldownScale === 'M5' ? 'NOISY MICRO SCALE' : 'STRUCTURAL FRAME'} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs" style={{ lineHeight: '1.8' }}>
            <div>
              <div style={{ color: 'var(--text-muted)' }}>Structure Role:</div>
              <div style={{ fontWeight: 'bold', color: 'var(--accent)' }}>
                {activeDrilldownScale === 'Monthly' || activeDrilldownScale === 'Weekly' || activeDrilldownScale === 'Daily' ? 'Macro Directional Context' :
                 activeDrilldownScale === 'H4' || activeDrilldownScale === 'H1' ? 'Active Base & Expansion Controller' : 'Internal Noise & Micro Timing'}
              </div>
            </div>
            <div>
              <div style={{ color: 'var(--text-muted)' }}>Current Phase:</div>
              <div style={{ fontWeight: 'bold', color: 'var(--primary)' }}>
                {activeDrilldownScale === 'H1' ? 'Expansion Preparation (Building Base)' :
                 activeDrilldownScale === 'Daily' ? 'Bullish Trend Continuation' : 'Return / Pullback'}
              </div>
            </div>
            <div>
              <div style={{ color: 'var(--text-muted)' }}>Controlling State:</div>
              <div style={{ fontWeight: 'bold' }}>
                {activeDrilldownScale === 'H1' ? 'Active Controlling Scale' : 'Internal Sub-Structure'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Active Fractal Report Card */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="card">
          <h3 className="text-sm font-bold text-[var(--primary)] uppercase tracking-wider mb-3">
            📋 Active Live Fractal Report (XAUUSD)
          </h3>
          <div style={{ lineHeight: '2', fontSize: '0.88rem' }}>
            <div><strong>Symbol:</strong> XAUUSD (Gold)</div>
            <div><strong>Dominant Scale:</strong> <span style={{ color: 'var(--primary)', fontWeight: 'bold' }}>H1 Frame</span></div>
            <div><strong>Higher Context:</strong> Daily Bullish Alignment</div>
            <div><strong>Current Structure:</strong> H1 Bullish Base (Range: $2,715.00 - $2,732.50)</div>
            <div><strong>Internal Base Behavior:</strong> Accumulation-like (4 Rotations, Compression, HH + HL)</div>
            <div><strong>Phase:</strong> Expansion Preparation</div>
            <div><strong>Expected Structural Behavior:</strong> Bullish Expansion → Continuation</div>
            <div><strong>Target Zone:</strong> <span style={{ color: 'var(--accent)', fontWeight: 'bold' }}>$2,755.00 - $2,770.00</span></div>
            <div><strong>Confidence Score:</strong> <ConfidenceBadge score={78.5} /></div>
          </div>
        </div>

        {/* Visual Chart Marking System Panel */}
        <div className="card" style={{ borderTop: '4px solid var(--accent)' }}>
          <h3 className="text-sm font-bold text-[var(--accent)] uppercase tracking-wider mb-3">
            📐 Chart Marking & Structural Annotations
          </h3>
          <p className="text-xs text-[var(--text-dark)] mb-3">
            Visual representation of price action structural zones marked on chart:
          </p>

          <div style={{ background: '#0B1420', padding: '15px', borderRadius: '8px', border: '1px dashed var(--primary)', position: 'relative', fontFamily: 'monospace', fontSize: '0.8rem', lineHeight: '1.6' }}>
            <div style={{ textAlign: 'right', color: 'var(--accent)' }}>▲ TARGET ZONE ($2,755.00 - $2,770.00)</div>
            <div style={{ paddingLeft: '40px', color: 'var(--primary)' }}>│</div>
            <div style={{ paddingLeft: '40px', color: 'var(--primary)' }}>│ ──▶ EXPANSION (Leg 1 Projected Speed: 4.2 $/hr)</div>
            <div style={{ paddingLeft: '40px', color: 'var(--primary)' }}>│</div>
            <div style={{ border: '1px solid var(--primary)', padding: '10px', borderRadius: '4px', background: 'rgba(227, 168, 59, 0.1)', color: 'var(--primary)' }}>
              ┌──────────────────────────────────────────────┐<br />
              │ BASE BOUNDARY: $2,715.00 - $2,732.50 (Duration: 18h) │<br />
              │ Behavior: Accumulation-like | Rotations: 4    │<br />
              └──────────────────────────────────────────────┘
            </div>
            <div style={{ paddingLeft: '20px', color: 'var(--warning)', marginTop: '6px' }}>▼ RETURN DEPTH (Expected 38.2% Fibonacci Pullback)</div>
            <div style={{ marginTop: '10px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              ANNOTATION STATUS: ACTIVE SCALE = H1 | FRACTAL DETECTED = YES
            </div>
          </div>
        </div>
      </div>

      {/* Historical Case Studies & Failure Analysis */}
      <div className="card">
        <h3 className="text-sm font-bold text-[var(--primary)] uppercase tracking-wider mb-3">
          📚 Historical Case Studies & Failure Analysis (50 Cases Sample)
        </h3>
        <p className="text-xs text-[var(--text-dark)] mb-4">
          Recorded outcomes from 500 multi-scale Base breakout opportunities across 2021–2026 replay.
        </p>

        <DataTable
          headers={['Fractal ID', 'Date/Time', 'Symbol', 'TF', 'Base Structure', 'Internal Behavior', 'Leg Sequence', 'Target Zone', 'Status', 'Result', 'Failure Explanation']}
          rows={historicalCases.map(row => [
            row.id,
            row.date,
            <strong>{row.symbol}</strong>,
            row.timeframe,
            row.base,
            row.internal,
            row.legSeq,
            row.targetZone,
            <StatusBadge status={row.status === 'Validated' ? 'passed' : 'failed'} label={row.status} />,
            row.result,
            <span style={{ color: row.failureCause !== '-' ? 'var(--danger)' : 'var(--text-dark)', fontSize: '0.8rem' }}>{row.failureCause}</span>
          ])}
        />
      </div>
    </div>
  );
}
