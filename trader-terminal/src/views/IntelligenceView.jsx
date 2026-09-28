import React from 'react';
import MetricCard from '../design-system/MetricCard';
import IntelligenceCard from '../design-system/IntelligenceCard';
import RiskCard from '../design-system/RiskCard';
import DecisionCard from '../design-system/DecisionCard';
import TimelineStepper from '../design-system/TimelineStepper';

export default function IntelligenceView({ t, signals, fractalStatus, regimeAnalysis, riskMetrics }) {
  return (
    <div id="shell-intel" className="space-y-6">
      <div className="card" style={{ borderLeft: '4px solid var(--accent)' }}>
        <h2 className="text-xl font-bold text-[var(--accent)] mb-2">🧠 YarTrader Autonomous Intelligence Operating System</h2>
        <p className="text-sm text-[var(--text-dark)] leading-relaxed">
          سیستم مدیریت و هوش مصنوعی اتونوموس: پردازش ساختار چندزمانه فرکتال، تحلیل رژیم بازار و موتور استدلال تصمیم‌گیری بدون اتکا به اندیکاتورهای کلاسیک.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <IntelligenceCard title="Fractal Evidence" score={fractalStatus?.fractal_score ?? null} regime={fractalStatus?.status || 'DATA UNAVAILABLE'} explanation={fractalStatus?.evidence_state || 'No verified fractal evidence available.'} />
        <RiskCard level={riskMetrics?.level || 'DATA UNAVAILABLE'} score={riskMetrics?.score ?? riskMetrics?.risk_score} maxLimit={riskMetrics?.max_limit} summary={riskMetrics?.summary || 'No verified risk telemetry available.'} />
        <IntelligenceCard title="Observed Market State" score={signals?.[0]?.confidence} regime={regimeAnalysis?.regime || regimeAnalysis?.state || signals?.[0]?.regime || 'DATA UNAVAILABLE'} explanation={signals?.[0]?.reason || signals?.[0]?.narrative || 'No verified market-state explanation available.'} />
      </div>

      <div className="card">
        <h3 className="text-sm font-bold text-[var(--primary)] uppercase tracking-wider mb-3">مسیر تصمیم‌گیری هوشمند (Decision Pipeline)</h3>
        <TimelineStepper steps={['دریافت داده متاتریدر', 'استخراج فرکتال', 'تایید رژیم نقدینگی', 'سنجش ریسک', 'صدور سیگنال']} currentStep={4} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <DecisionCard
          title="سیگنال خرید طلا (XAUUSD Buy Setup)"
          recommendation={signals?.[0]?.direction || signals?.[0]?.action || 'WAIT'}
          confidence={signals?.[0]?.confidence}
          rr={signals?.[0]?.risk_reward != null ? String(signals[0].risk_reward) : undefined}
          reason={signals?.[0]?.reason || signals?.[0]?.narrative || 'No verified decision rationale is available.'}
        />
        <DecisionCard
          title="سیگنال یورو دلار (EURUSD Wait Setup)"
          recommendation="WAIT / HOLD"
          confidence={45}
          rr="1 : 1.1"
          reason="عدم شفافیت در رژیم نقدینگی تایم‌فریم H4. سفارش مسدود گردید."
        />
      </div>
    </div>
  );
}
