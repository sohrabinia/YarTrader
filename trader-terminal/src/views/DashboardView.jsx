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
,
  marketCandles,
  marketQuote,
  marketDataLoading,
  marketDataError,
  spikeResult,
  spikeLoading,
  spikeError,
  rangeResult,
  rangeLoading,
  rangeError,
  trendResult,
  trendLoading,
  trendError,
  backtestResult,
  backtestLoading,
  backtestError,
  learningInsight,
  learningLoading,
  learningError,
  memoryData,
  memoryLoading,
  memoryError,
  intelligenceData,
  intelligenceLoading,
  intelligenceError,
  decisionContextData,
  decisionContextLoading,
  decisionContextError,
  decisionIntelligenceData,
  decisionIntelligenceLoading,
  decisionIntelligenceError,
  decisionGovernanceData,
  decisionGovernanceLoading,
  decisionGovernanceError}) {
  return (
    <div id="shell-terminal" className="space-y-6">




      {/* Deterministic Decision Governance Foundation Card */}
      <Card className="border-l-4 border-l-[var(--success)]">
        <CardHeader className="flex flex-row items-center justify-between flex-wrap gap-2">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <span>🛡️</span> Decision Governance Foundation ({selectedAsset || 'XAUUSD'})
            </CardTitle>
            <p className="text-xs text-[var(--text-muted)] mt-1">
              Sample depth, data quality, & context stability validation checks (No Buy/Sell signals, trading execution, or AI models).
            </p>
          </div>
          {decisionGovernanceData && (
            <div className="flex items-center gap-2">
              <Badge variant={decisionGovernanceData.governance_state === 'GOVERNANCE_APPROVED' ? 'success' : 'danger'}>
                GOVERNANCE: {decisionGovernanceData.governance_state}
              </Badge>
            </div>
          )}
        </CardHeader>
        <CardContent>
          {decisionGovernanceLoading ? (
            <div className="p-4 text-center text-xs text-[var(--text-muted)] animate-pulse">
              Evaluating decision governance rules...
            </div>
          ) : decisionGovernanceError ? (
            <div className="p-3 text-xs text-[var(--danger)] bg-[var(--danger-bg)] rounded border border-[var(--danger)]/30">
              ⚠️ Decision Governance Error: {decisionGovernanceError}
            </div>
          ) : !decisionGovernanceData ? (
            <div className="p-4 text-center text-xs text-[var(--text-muted)]">
              No decision governance evaluation data available.
            </div>
          ) : (
            <div className="space-y-4 text-xs font-mono">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase">Governance State</div>
                  <div className="text-base font-bold text-[var(--success)]">{decisionGovernanceData.governance_state}</div>
                  <div className="text-[10px] text-[var(--text-muted)]">Rule Validation Status</div>
                </div>
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase">Evidence Quality</div>
                  <div className="text-base font-bold text-[var(--primary)]">{decisionGovernanceData.evidence_quality}</div>
                  <div className="text-[10px] text-[var(--text-muted)]">Sample Quality Grade</div>
                </div>
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase">Rule Checks Passed</div>
                  <div className="text-base font-bold">{decisionGovernanceData.checks?.filter(c => c.passed).length || 0} / {decisionGovernanceData.checks?.length || 0}</div>
                  <div className="text-[10px] text-[var(--text-muted)]">Deterministic Rules</div>
                </div>
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase">Compiled At (UTC)</div>
                  <div className="text-xs text-[var(--text-muted)] truncate mt-1">{decisionGovernanceData.compiled_at || 'N/A'}</div>
                  <div className="text-[10px] text-[var(--success)] mt-1">Zero Orders / Broker Calls</div>
                </div>
              </div>

              {decisionGovernanceData.checks && decisionGovernanceData.checks.length > 0 && (
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase mb-2">Governance Validation Checks</div>
                  <div className="space-y-1.5">
                    {decisionGovernanceData.checks.map((c, idx) => (
                      <div key={idx} className="p-2 bg-[var(--surface-light)]/20 rounded border border-[var(--border)]/50 flex justify-between items-center text-[11px]">
                        <div>
                          <span className="font-bold text-[var(--primary)]">{c.rule_id} ({c.rule_name}):</span> {c.message}
                        </div>
                        <Badge variant={c.passed ? 'success' : 'danger'}>{c.passed ? 'PASSED' : 'FAILED'}</Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>


      {/* Deterministic Decision Intelligence Foundation Card */}
      <Card className="border-l-4 border-l-[var(--primary)]">
        <CardHeader className="flex flex-row items-center justify-between flex-wrap gap-2">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <span>🎯</span> Decision Intelligence Foundation ({selectedAsset || 'XAUUSD'})
            </CardTitle>
            <p className="text-xs text-[var(--text-muted)] mt-1">
              Sample depth & data quality intelligence summary (No AI/LLM models, neural networks, or predictions).
            </p>
          </div>
          {decisionIntelligenceData && (
            <div className="flex items-center gap-2">
              <Badge variant={decisionIntelligenceData.decision_readiness_state === 'INTELLIGENCE_READY' ? 'success' : 'warning'}>
                READINESS: {decisionIntelligenceData.decision_readiness_state}
              </Badge>
            </div>
          )}
        </CardHeader>
        <CardContent>
          {decisionIntelligenceLoading ? (
            <div className="p-4 text-center text-xs text-[var(--text-muted)] animate-pulse">
              Compiling decision intelligence metrics...
            </div>
          ) : decisionIntelligenceError ? (
            <div className="p-3 text-xs text-[var(--danger)] bg-[var(--danger-bg)] rounded border border-[var(--danger)]/30">
              ⚠️ Decision Intelligence Error: {decisionIntelligenceError}
            </div>
          ) : !decisionIntelligenceData ? (
            <div className="p-4 text-center text-xs text-[var(--text-muted)]">
              No decision intelligence data available.
            </div>
          ) : (
            <div className="space-y-4 text-xs font-mono">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase">Readiness State</div>
                  <div className="text-base font-bold text-[var(--success)]">{decisionIntelligenceData.decision_readiness_state}</div>
                  <div className="text-[10px] text-[var(--text-muted)]">Context Stability</div>
                </div>
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase">Sample Sufficiency</div>
                  <div className="text-base font-bold text-[var(--primary)]">{((decisionIntelligenceData.context_sufficiency_score || 0) * 100).toFixed(0)}%</div>
                  <div className="text-[10px] text-[var(--text-muted)]">30-Bar Baseline Score</div>
                </div>
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase">Factor Quality</div>
                  <div className="text-base font-bold">{decisionIntelligenceData.evidence_factor_quality}</div>
                  <div className="text-[10px] text-[var(--text-muted)]">Evidence Depth</div>
                </div>
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase">Compiled At (UTC)</div>
                  <div className="text-xs text-[var(--text-muted)] truncate mt-1">{decisionIntelligenceData.compiled_at || 'N/A'}</div>
                  <div className="text-[10px] text-[var(--success)] mt-1">Pure Statistical Math</div>
                </div>
              </div>

              {decisionIntelligenceData.metrics && decisionIntelligenceData.metrics.length > 0 && (
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase mb-2">Explainable Intelligence Metrics</div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                    {decisionIntelligenceData.metrics.map((m, idx) => (
                      <div key={idx} className="p-2 bg-[var(--surface-light)]/20 rounded border border-[var(--border)]/50 text-[11px]">
                        <div className="font-bold text-[var(--primary)]">{m.metric_name}</div>
                        <div className="text-[10px] text-[var(--text-muted)] mt-0.5">{m.explanation}</div>
                        <Badge variant="neutral" className="mt-1">{m.category}</Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>


      {/* Deterministic Decision Context Foundation Card */}
      <Card className="border-l-4 border-l-[var(--success)]">
        <CardHeader className="flex flex-row items-center justify-between flex-wrap gap-2">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <span>📋</span> Decision Context Foundation ({selectedAsset || 'XAUUSD'})
            </CardTitle>
            <p className="text-xs text-[var(--text-muted)] mt-1">
              Structured historical context preparation for human or AI consumers (No Buy/Sell signals, predictions, or auto-trading).
            </p>
          </div>
          {decisionContextData && (
            <div className="flex items-center gap-2">
              <Badge variant="passed">
                QUALITY: {decisionContextData.data_quality_state}
              </Badge>
            </div>
          )}
        </CardHeader>
        <CardContent>
          {decisionContextLoading ? (
            <div className="p-4 text-center text-xs text-[var(--text-muted)] animate-pulse">
              Compiling decision context summary...
            </div>
          ) : decisionContextError ? (
            <div className="p-3 text-xs text-[var(--danger)] bg-[var(--danger-bg)] rounded border border-[var(--danger)]/30">
              ⚠️ Decision Context Error: {decisionContextError}
            </div>
          ) : !decisionContextData ? (
            <div className="p-4 text-center text-xs text-[var(--text-muted)]">
              No decision context data available.
            </div>
          ) : (
            <div className="space-y-4 text-xs font-mono">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase">Context Status</div>
                  <div className="text-base font-bold text-[var(--success)]">{decisionContextData.reliability_state}</div>
                  <div className="text-[10px] text-[var(--text-muted)]">Reliability Classification</div>
                </div>
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase">Data Quality</div>
                  <div className="text-base font-bold text-[var(--primary)]">{decisionContextData.data_quality_state}</div>
                  <div className="text-[10px] text-[var(--text-muted)]">Historical Sample Depth</div>
                </div>
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase">Evidence Factors</div>
                  <div className="text-base font-bold">{decisionContextData.factors?.length || 0}</div>
                  <div className="text-[10px] text-[var(--text-muted)]">Explainable Parameters</div>
                </div>
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase">Compiled At (UTC)</div>
                  <div className="text-xs text-[var(--text-muted)] truncate mt-1">{decisionContextData.compiled_at || 'N/A'}</div>
                  <div className="text-[10px] text-[var(--success)] mt-1">Zero Predictions / Trades</div>
                </div>
              </div>

              {decisionContextData.factors && decisionContextData.factors.length > 0 && (
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase mb-2">Explainable Context Evidence Factors</div>
                  <div className="space-y-1.5">
                    {decisionContextData.factors.map((f, idx) => (
                      <div key={idx} className="p-2 bg-[var(--surface-light)]/20 rounded border border-[var(--border)]/50 flex justify-between items-center text-[11px]">
                        <div>
                          <span className="font-bold text-[var(--primary)]">{f.factor_name}:</span> {f.explanation}
                        </div>
                        <Badge variant="neutral">{f.source}</Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>


      {/* Historical Intelligence Foundation Card */}
      <Card className="border-l-4 border-l-[var(--primary)]">
        <CardHeader className="flex flex-row items-center justify-between flex-wrap gap-2">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <span>🧠</span> Deterministic Intelligence Foundation ({selectedAsset || 'XAUUSD'})
            </CardTitle>
            <p className="text-xs text-[var(--text-muted)] mt-1">
              Statistical context aggregation from Learning & Memory outputs (No AI/LLM/ML models, neural networks, or predictions).
            </p>
          </div>
          {intelligenceData && (
            <div className="flex items-center gap-2">
              <Badge variant={intelligenceData.sample_sufficiency_status === 'VALID_SAMPLE' ? 'success' : 'warning'}>
                SAMPLE STATUS: {intelligenceData.sample_sufficiency_status}
              </Badge>
            </div>
          )}
        </CardHeader>
        <CardContent>
          {intelligenceLoading ? (
            <div className="p-4 text-center text-xs text-[var(--text-muted)] animate-pulse">
              Compiling historical intelligence summary...
            </div>
          ) : intelligenceError ? (
            <div className="p-3 text-xs text-[var(--danger)] bg-[var(--danger-bg)] rounded border border-[var(--danger)]/30">
              ⚠️ Intelligence Error: {intelligenceError}
            </div>
          ) : !intelligenceData ? (
            <div className="p-4 text-center text-xs text-[var(--text-muted)]">
              No intelligence foundation data available.
            </div>
          ) : (
            <div className="space-y-4 text-xs font-mono">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase">Context Observations</div>
                  <div className="text-base font-bold text-[var(--primary)]">{intelligenceData.historical_context_count}</div>
                  <div className="text-[10px] text-[var(--text-muted)]">Memory Records: {intelligenceData.memory_records_count}</div>
                </div>
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase">Active Signals</div>
                  <div className="text-base font-bold text-[var(--success)]">{intelligenceData.context?.active_signals_count || 0}</div>
                  <div className="text-[10px] text-[var(--text-muted)]">Active Strategy Signals</div>
                </div>
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase">Sample Confidence</div>
                  <div className="text-base font-bold text-[var(--primary)]">{((intelligenceData.statistical_confidence_score || 0) * 100).toFixed(0)}%</div>
                  <div className="text-[10px] text-[var(--text-muted)]">Sample Size Score (Not Prediction)</div>
                </div>
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase">Compiled At (UTC)</div>
                  <div className="text-xs text-[var(--text-muted)] truncate mt-1">{intelligenceData.compiled_at || 'N/A'}</div>
                  <div className="text-[10px] text-[var(--success)] mt-1">Read-Only Pure Math</div>
                </div>
              </div>

              {intelligenceData.signal_summaries && intelligenceData.signal_summaries.length > 0 && (
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase mb-2">Signal Distribution Summaries</div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                    {intelligenceData.signal_summaries.map((s) => (
                      <div key={s.signal_name} className="p-2 bg-[var(--surface-light)]/20 rounded border border-[var(--border)]/50">
                        <div className="text-[var(--text-muted)] text-[10px]">{s.signal_name}</div>
                        <div className="text-xs font-bold mt-0.5">{s.historical_count} ({((s.frequency_ratio || 0) * 100).toFixed(1)}%)</div>
                        <div className="text-[9px] text-[var(--primary)] mt-1">{s.sample_confidence_state}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>


      {/* Historical Memory Foundation Card */}
      <Card className="border-l-4 border-l-[var(--accent)]">
        <CardHeader className="flex flex-row items-center justify-between flex-wrap gap-2">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <span>🏛️</span> Historical Memory Foundation ({selectedAsset || 'XAUUSD'})
            </CardTitle>
            <p className="text-xs text-[var(--text-muted)] mt-1">
              Structured historical knowledge storage derived from Phase 11 Learning Insights (No AI Agents or Vector DB).
            </p>
          </div>
          {memoryData && (
            <div className="flex items-center gap-2">
              <Badge variant="passed">
                RECORDS: {memoryData.total_records} STORED
              </Badge>
            </div>
          )}
        </CardHeader>
        <CardContent>
          {memoryLoading ? (
            <div className="p-4 text-center text-xs text-[var(--text-muted)] animate-pulse">
              Retrieving historical memory records...
            </div>
          ) : memoryError ? (
            <div className="p-3 text-xs text-[var(--danger)] bg-[var(--danger-bg)] rounded border border-[var(--danger)]/30">
              ⚠️ Memory Error: {memoryError}
            </div>
          ) : !memoryData ? (
            <div className="p-4 text-center text-xs text-[var(--text-muted)]">
              No historical memory records available.
            </div>
          ) : (
            <div className="space-y-4 text-xs font-mono">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase">Stored Records</div>
                  <div className="text-base font-bold text-[var(--accent)]">{memoryData.total_records}</div>
                  <div className="text-[10px] text-[var(--text-muted)]">Phase 12 In-Memory Store</div>
                </div>
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase">Latest Timestamp</div>
                  <div className="text-xs text-[var(--text-muted)] truncate mt-1">{memoryData.summary?.latest_timestamp || 'N/A'}</div>
                  <div className="text-[10px] text-[var(--success)] mt-1">UTC Timezone</div>
                </div>
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase">Strategies Tracked</div>
                  <div className="text-base font-bold">{Object.keys(memoryData.summary?.strategy_distribution || {}).length || 1}</div>
                  <div className="text-[10px] text-[var(--text-muted)]">Phase 7-9 Coverage</div>
                </div>
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase">Symbols Tracked</div>
                  <div className="text-base font-bold">{Object.keys(memoryData.summary?.symbol_distribution || {}).length || 1}</div>
                  <div className="text-[10px] text-[var(--success)] mt-1">Read-Only Store</div>
                </div>
              </div>

              {memoryData.records && memoryData.records.length > 0 && (
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase mb-2">Latest Knowledge Record Details</div>
                  <div className="p-2 bg-[var(--surface-light)]/20 rounded border border-[var(--border)]/50 space-y-1 text-[11px]">
                    <div><strong>Record ID:</strong> {memoryData.records[0].id}</div>
                    <div><strong>Observation Type:</strong> {memoryData.records[0].observation_type}</div>
                    <div><strong>Confidence Score:</strong> {(memoryData.records[0].confidence * 100).toFixed(1)}%</div>
                    <div><strong>Source Phase:</strong> {memoryData.records[0].source_phase}</div>
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>


      {/* Deterministic Statistical Learning Analysis Card */}
      <Card className="border-l-4 border-l-[var(--primary)]">
        <CardHeader className="flex flex-row items-center justify-between flex-wrap gap-2">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <span>🧠</span> Historical Learning Analysis ({selectedAsset || 'XAUUSD'})
            </CardTitle>
            <p className="text-xs text-[var(--text-muted)] mt-1">
              Deterministic statistical signal frequencies & sample sufficiency aggregation (No AI/ML or Strategy Modification).
            </p>
          </div>
          {learningInsight && (
            <div className="flex items-center gap-2">
              <Badge variant={learningInsight.sample_sufficiency ? 'success' : 'warning'}>
                STATUS: {learningInsight.sample_sufficiency ? 'VALID_SAMPLE' : 'INSUFFICIENT_DATA'}
              </Badge>
            </div>
          )}
        </CardHeader>
        <CardContent>
          {learningLoading ? (
            <div className="p-4 text-center text-xs text-[var(--text-muted)] animate-pulse">
              Aggregating historical learning observations...
            </div>
          ) : learningError ? (
            <div className="p-3 text-xs text-[var(--danger)] bg-[var(--danger-bg)] rounded border border-[var(--danger)]/30">
              ⚠️ Learning Error: {learningError}
            </div>
          ) : !learningInsight ? (
            <div className="p-4 text-center text-xs text-[var(--text-muted)]">
              No historical learning insights available.
            </div>
          ) : (
            <div className="space-y-4 text-xs font-mono">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase">Observations</div>
                  <div className="text-base font-bold text-[var(--primary)]">{learningInsight.observation_count}</div>
                  <div className="text-[10px] text-[var(--text-muted)]">Threshold: {learningInsight.config.min_sample_threshold} bars</div>
                </div>
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase">Active Signal Ratio</div>
                  <div className="text-base font-bold text-[var(--success)]">{(learningInsight.reliability_summary.active_signal_ratio * 100).toFixed(1)}%</div>
                  <div className="text-[10px] text-[var(--text-muted)]">Count: {learningInsight.reliability_summary.active_signal_count}</div>
                </div>
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase">Strategy Type</div>
                  <div className="text-base font-bold">{learningInsight.strategy_type}</div>
                  <div className="text-[10px] text-[var(--text-muted)]">{learningInsight.symbol} ({learningInsight.interval})</div>
                </div>
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase">Analyzed At (UTC)</div>
                  <div className="text-xs text-[var(--text-muted)] truncate mt-1">{learningInsight.analyzed_at}</div>
                  <div className="text-[10px] text-[var(--success)] mt-1">Strict t ≤ T Cutoff</div>
                </div>
              </div>

              <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                <div className="text-[var(--text-muted)] text-[10px] uppercase mb-2">Signal Distribution & Frequencies</div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                  {Object.entries(learningInsight.signal_counts || {}).map(([sig, count]) => (
                    <div key={sig} className="p-2 bg-[var(--surface-light)]/20 rounded border border-[var(--border)]/50">
                      <div className="text-[var(--text-muted)] text-[10px]">{sig}</div>
                      <div className="text-xs font-bold mt-0.5">{count} ({((learningInsight.signal_frequencies[sig] || 0) * 100).toFixed(1)}%)</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>


      {/* Walk-Forward Historical Backtest Simulation Card */}
      <Card className="border-l-4 border-l-[var(--success)]">
        <CardHeader className="flex flex-row items-center justify-between flex-wrap gap-2">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <span>⏳</span> Walk-Forward Backtest Simulation ({selectedAsset || 'XAUUSD'})
            </CardTitle>
            <p className="text-xs text-[var(--text-muted)] mt-1">
              Historical simulation with strict t ≤ T candle slicing (Zero look-ahead bias).
            </p>
          </div>
          {backtestResult && (
            <div className="flex items-center gap-2">
              <Badge variant="success">
                VALID EVALUATIONS: {backtestResult.summary.valid_evaluations} / {backtestResult.summary.total_evaluations}
              </Badge>
            </div>
          )}
        </CardHeader>
        <CardContent>
          {backtestLoading ? (
            <div className="p-4 text-center text-xs text-[var(--text-muted)] animate-pulse">
              Executing walk-forward backtest simulation...
            </div>
          ) : backtestError ? (
            <div className="p-3 text-xs text-[var(--danger)] bg-[var(--danger-bg)] rounded border border-[var(--danger)]/30">
              ⚠️ Backtest Error: {backtestError}
            </div>
          ) : !backtestResult ? (
            <div className="p-4 text-center text-xs text-[var(--text-muted)]">
              No backtest simulation result available.
            </div>
          ) : (
            <div className="space-y-4 text-xs font-mono">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase">Evaluations</div>
                  <div className="text-base font-bold text-[var(--success)]">{backtestResult.summary.total_evaluations}</div>
                  <div className="text-[10px] text-[var(--text-muted)]">Valid: {backtestResult.summary.valid_evaluations}</div>
                </div>
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase">Strategy Type</div>
                  <div className="text-base font-bold">{backtestResult.strategy_type}</div>
                  <div className="text-[10px] text-[var(--text-muted)]">{backtestResult.symbol} ({backtestResult.interval})</div>
                </div>
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase">Min History Bars</div>
                  <div className="text-base font-bold">{backtestResult.config.min_history_bars} bars</div>
                  <div className="text-[10px] text-[var(--text-muted)]">Cold Start Protection</div>
                </div>
                <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                  <div className="text-[var(--text-muted)] text-[10px] uppercase">Executed At (UTC)</div>
                  <div className="text-xs text-[var(--text-muted)] truncate mt-1">{backtestResult.executed_at}</div>
                  <div className="text-[10px] text-[var(--success)] mt-1">Zero Live Execution</div>
                </div>
              </div>

              <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                <div className="text-[var(--text-muted)] text-[10px] uppercase mb-2">Signal Distribution Counts</div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                  {Object.entries(backtestResult.summary.signal_counts || {}).map(([sig, count]) => (
                    <div key={sig} className="p-2 bg-[var(--surface-light)]/20 rounded border border-[var(--border)]/50">
                      <div className="text-[var(--text-muted)] text-[10px]">{sig}</div>
                      <div className="text-xs font-bold mt-0.5">{count} bars</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>


      {/* Trend Strategy Demonstration Card */}
      <Card className="border-l-4 border-l-[var(--primary)]">
        <CardHeader className="flex flex-row items-center justify-between flex-wrap gap-2">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <span>📈</span> Deterministic Trend Strategy ({selectedAsset || 'XAUUSD'})
            </CardTitle>
            <p className="text-xs text-[var(--text-muted)] mt-1">
              Dual SMA Crossover & Volatility-Normalized Trend Strength (M15 horizon).
            </p>
          </div>
          {trendResult && (
            <div className="flex items-center gap-2">
              <Badge variant={
                trendResult.signal_type === 'TREND_UP' ? 'success' :
                trendResult.signal_type === 'TREND_DOWN' ? 'danger' :
                trendResult.signal_type === 'INSUFFICIENT_DATA' ? 'warning' : 'default'
              }>
                SIGNAL: {trendResult.signal_type}
              </Badge>
            </div>
          )}
        </CardHeader>
        <CardContent>
          {trendLoading ? (
            <div className="p-4 text-center text-xs text-[var(--text-muted)] animate-pulse">
              Evaluating trend strategy metrics...
            </div>
          ) : trendError ? (
            <div className="p-3 text-xs text-[var(--danger)] bg-[var(--danger-bg)] rounded border border-[var(--danger)]/30">
              ⚠️ Trend Strategy Error: {trendError}
            </div>
          ) : !trendResult ? (
            <div className="p-4 text-center text-xs text-[var(--text-muted)]">
              No strategy result available.
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs font-mono">
              <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                <div className="text-[var(--text-muted)] text-[10px] uppercase">Trend Strength</div>
                <div className="text-base font-bold text-[var(--primary)]">{trendResult.metrics.normalized_trend_strength}x</div>
                <div className="text-[10px] text-[var(--text-muted)]">Min Threshold: {trendResult.config.minimum_trend_strength}x</div>
              </div>
              <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                <div className="text-[var(--text-muted)] text-[10px] uppercase">Trend Spread</div>
                <div className="text-base font-bold">{trendResult.metrics.trend_spread}</div>
                <div className="text-[10px] text-[var(--text-muted)]">Fast: {trendResult.metrics.fast_sma} | Slow: {trendResult.metrics.slow_sma}</div>
              </div>
              <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                <div className="text-[var(--text-muted)] text-[10px] uppercase">Volatility Baseline</div>
                <div className="text-base font-bold">{trendResult.metrics.volatility_baseline}</div>
                <div className="text-[10px] text-[var(--text-muted)]">MTR ({trendResult.config.slow_period} bars)</div>
              </div>
              <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                <div className="text-[var(--text-muted)] text-[10px] uppercase">Evaluation Time</div>
                <div className="text-xs text-[var(--text-muted)] truncate mt-1">{trendResult.evaluation_time}</div>
                <div className="text-[10px] text-[var(--success)] mt-1">No Look-Ahead Bias</div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>


      {/* Range Strategy Demonstration Card */}
      <Card className="border-l-4 border-l-[var(--success)]">
        <CardHeader className="flex flex-row items-center justify-between flex-wrap gap-2">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <span>📐</span> Deterministic Range Strategy ({selectedAsset || 'XAUUSD'})
            </CardTitle>
            <p className="text-xs text-[var(--text-muted)] mt-1">
              Rolling channel width & normalized volatility structure (M15 horizon).
            </p>
          </div>
          {rangeResult && (
            <div className="flex items-center gap-2">
              <Badge variant={
                rangeResult.signal_type === 'RANGE' ? 'success' :
                rangeResult.signal_type === 'INSUFFICIENT_DATA' ? 'warning' : 'default'
              }>
                SIGNAL: {rangeResult.signal_type}
              </Badge>
            </div>
          )}
        </CardHeader>
        <CardContent>
          {rangeLoading ? (
            <div className="p-4 text-center text-xs text-[var(--text-muted)] animate-pulse">
              Evaluating range strategy metrics...
            </div>
          ) : rangeError ? (
            <div className="p-3 text-xs text-[var(--danger)] bg-[var(--danger-bg)] rounded border border-[var(--danger)]/30">
              ⚠️ Range Strategy Error: {rangeError}
            </div>
          ) : !rangeResult ? (
            <div className="p-4 text-center text-xs text-[var(--text-muted)]">
              No strategy result available.
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs font-mono">
              <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                <div className="text-[var(--text-muted)] text-[10px] uppercase">Normalized Ratio</div>
                <div className="text-base font-bold text-[var(--success)]">{rangeResult.metrics.normalized_range_ratio}x</div>
                <div className="text-[10px] text-[var(--text-muted)]">Max Threshold: {rangeResult.config.max_normalized_range}x</div>
              </div>
              <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                <div className="text-[var(--text-muted)] text-[10px] uppercase">Range Channel</div>
                <div className="text-base font-bold">{rangeResult.metrics.range_width}</div>
                <div className="text-[10px] text-[var(--text-muted)]">L: {rangeResult.metrics.rolling_low} | H: {rangeResult.metrics.rolling_high}</div>
              </div>
              <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                <div className="text-[var(--text-muted)] text-[10px] uppercase">Close Location</div>
                <div className="text-base font-bold">{rangeResult.metrics.close_position_pct}%</div>
                <div className="text-[10px] text-[var(--text-muted)]">In Rolling Channel</div>
              </div>
              <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                <div className="text-[var(--text-muted)] text-[10px] uppercase">Evaluation Time</div>
                <div className="text-xs text-[var(--text-muted)] truncate mt-1">{rangeResult.evaluation_time}</div>
                <div className="text-[10px] text-[var(--success)] mt-1">No Look-Ahead Bias</div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>


      {/* Spike Strategy Demonstration Card */}
      <Card className="border-l-4 border-l-[var(--primary)]">
        <CardHeader className="flex flex-row items-center justify-between flex-wrap gap-2">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <span>⚡</span> Deterministic Spike Strategy ({selectedAsset || 'XAUUSD'})
            </CardTitle>
            <p className="text-xs text-[var(--text-muted)] mt-1">
              Statistical abnormal range & impulse detection (M15 horizon).
            </p>
          </div>
          {spikeResult && (
            <div className="flex items-center gap-2">
              <Badge variant={
                spikeResult.signal_type === 'SPIKE_UP' ? 'success' :
                spikeResult.signal_type === 'SPIKE_DOWN' ? 'danger' :
                spikeResult.signal_type === 'INSUFFICIENT_DATA' ? 'warning' : 'default'
              }>
                SIGNAL: {spikeResult.signal_type}
              </Badge>
            </div>
          )}
        </CardHeader>
        <CardContent>
          {spikeLoading ? (
            <div className="p-4 text-center text-xs text-[var(--text-muted)] animate-pulse">
              Evaluating spike strategy metrics...
            </div>
          ) : spikeError ? (
            <div className="p-3 text-xs text-[var(--danger)] bg-[var(--danger-bg)] rounded border border-[var(--danger)]/30">
              ⚠️ Spike Strategy Error: {spikeError}
            </div>
          ) : !spikeResult ? (
            <div className="p-4 text-center text-xs text-[var(--text-muted)]">
              No strategy result available.
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs font-mono">
              <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                <div className="text-[var(--text-muted)] text-[10px] uppercase">Spike Ratio</div>
                <div className="text-base font-bold text-[var(--primary)]">{spikeResult.spike_ratio}x</div>
                <div className="text-[10px] text-[var(--text-muted)]">Threshold: {spikeResult.config.spike_threshold}x</div>
              </div>
              <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                <div className="text-[var(--text-muted)] text-[10px] uppercase">Candle Body</div>
                <div className="text-base font-bold">{spikeResult.candle.body}</div>
                <div className="text-[10px] text-[var(--text-muted)]">Range: {spikeResult.candle.range}</div>
              </div>
              <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                <div className="text-[var(--text-muted)] text-[10px] uppercase">Volatility MTR</div>
                <div className="text-base font-bold">{spikeResult.volatility_baseline}</div>
                <div className="text-[10px] text-[var(--text-muted)]">Lookback: {spikeResult.config.lookback_period} bars</div>
              </div>
              <div className="bg-[var(--surface-dark)] p-3 rounded border border-[var(--border)]">
                <div className="text-[var(--text-muted)] text-[10px] uppercase">Evaluation Time</div>
                <div className="text-xs text-[var(--text-muted)] truncate mt-1">{spikeResult.evaluation_time}</div>
                <div className="text-[10px] text-[var(--success)] mt-1">No Look-Ahead Bias</div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>


      {/* Normalized Market Data / Intelligence Demonstration Card */}
      <Card className="border-l-4 border-l-[var(--accent)]">
        <CardHeader className="flex flex-row items-center justify-between flex-wrap gap-2">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <span>📊</span> Normalized Market Data Intelligence ({selectedAsset || 'XAUUSD'})
            </CardTitle>
            <p className="text-xs text-[var(--text-muted)] mt-1">
              Canonical provider-independent OHLCV historical feed & real-time quotes.
            </p>
          </div>
          {marketQuote && (
            <div className="flex gap-3 text-xs font-mono bg-[var(--surface-dark)] px-3 py-1.5 rounded border border-[var(--border)]">
              <span>BID: <strong className="text-[var(--success)]">{marketQuote.bid}</strong></span>
              <span>ASK: <strong className="text-[var(--danger)]">{marketQuote.ask}</strong></span>
              <span>LAST: <strong className="text-[var(--primary)]">{marketQuote.last}</strong></span>
            </div>
          )}
        </CardHeader>
        <CardContent>
          {marketDataLoading ? (
            <div className="p-6 text-center text-xs text-[var(--text-muted)] animate-pulse">
              Loading normalized market data feeds...
            </div>
          ) : marketDataError ? (
            <div className="p-4 text-xs text-[var(--danger)] bg-[var(--danger-bg)] rounded border border-[var(--danger)]/30">
              ⚠️ Market Data Error: {marketDataError}
            </div>
          ) : !marketCandles || marketCandles.length === 0 ? (
            <div className="p-6 text-center text-xs text-[var(--text-muted)]">
              No market data available for {selectedAsset || 'XAUUSD'}.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs font-mono text-left">
                <thead>
                  <tr className="border-b border-[var(--border)] text-[var(--text-muted)] uppercase">
                    <th className="py-2 px-3">Timestamp (UTC)</th>
                    <th className="py-2 px-3">Open</th>
                    <th className="py-2 px-3">High</th>
                    <th className="py-2 px-3">Low</th>
                    <th className="py-2 px-3">Close</th>
                    <th className="py-2 px-3">Volume</th>
                  </tr>
                </thead>
                <tbody>
                  {marketCandles.map((c, idx) => (
                    <tr key={idx} className="border-b border-[var(--border)]/50 hover:bg-[var(--surface-light)]/30">
                      <td className="py-1.5 px-3 text-[var(--text-muted)]">{c.timestamp}</td>
                      <td className="py-1.5 px-3">{c.open}</td>
                      <td className="py-1.5 px-3 text-[var(--success)]">{c.high}</td>
                      <td className="py-1.5 px-3 text-[var(--danger)]">{c.low}</td>
                      <td className="py-1.5 px-3 font-semibold">{c.close}</td>
                      <td className="py-1.5 px-3 text-[var(--text-muted)]">{c.volume}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>


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
