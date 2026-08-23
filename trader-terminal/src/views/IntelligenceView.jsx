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
        <IntelligenceCard title="تحلیل فرکتال (Fractal Engine)" score={88} regime="BULLISH EXPANSION" explanation="تشخیص الگوی تکرارشونده Base Detector v1.1 در تایم‌فریم‌های M5 و H1." />
        <RiskCard level="LOW" score={15} maxLimit={50} summary="ریسک کلی پورتفوی در محدوده امن. حد ضرر شناور و نسبت سود به زیان > 1.8." />
        <IntelligenceCard title="رژیم بازار (Market Regime)" score={92} regime="HIGH LIQUIDITY / TRENDING" explanation="تراکم نقدینگی در نواحی Swing High و جذب اردرهای نهادی." />
      </div>

      <div className="card">
        <h3 className="text-sm font-bold text-[var(--primary)] uppercase tracking-wider mb-3">مسیر تصمیم‌گیری هوشمند (Decision Pipeline)</h3>
        <TimelineStepper steps={['دریافت داده متاتریدر', 'استخراج فرکتال', 'تایید رژیم نقدینگی', 'سنجش ریسک', 'صدور سیگنال']} currentStep={4} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <DecisionCard
          title="سیگنال خرید طلا (XAUUSD Buy Setup)"
          recommendation="BUY / LONG"
          confidence={87}
          rr="1 : 2.4"
          reason="شکست ساختار (BOS) در M15 + پولبک به ناحیه تقاضای Base"
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
