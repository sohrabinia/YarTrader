import React from 'react';
import MetricCard from '../design-system/MetricCard';
import ChartContainer from '../design-system/ChartContainer';
import ConfidenceBadge from '../design-system/ConfidenceBadge';
import PositionTimelineStepper from '../design-system/PositionTimelineStepper';

const copy = {
  fa: { env:'محیط', safety:'گیت ایمنی', data:'داده', live:'زنده', unreachable:'قطع اتصال', demo:'دمو', liveIn:'دریافت زنده', unavailable:'داده در دسترس نیست', mock:'دریافت آزمایشی', gateOff:'Fail-Closed / LIVE غیرفعال', gateOn:'LIVE فعال', session:'وضعیت نشست بازار', inference:'استنتاج', qualified:'چیدمان واجد شرایط', feasibility:'امکان‌سنجی ورود ۱۲۰ ثانیه', passed:'تأیید شد', tp:'امکان‌سنجی زمان TP', validated:'اعتبارسنجی شد', eligibility:'صلاحیت اجرا', demoEligible:'واجد شرایط DEMO', chart:'ساختار قیمت و نقشه نقدینگی', structure:'نقشه ساختار (HH / HL / LH / LL)', narrative:'ساختار بازار در تایم‌فریم‌های مرجع بررسی می‌شود؛ هیچ اندیکاتور کلاسیکی در مسیر اجرایی استفاده نمی‌شود.', lifecycle:'خط لوله چرخه عمر موقعیت' },
  en: { env:'Environment', safety:'Safety Gate', data:'Data', live:'LIVE', unreachable:'UNREACHABLE', demo:'DEMO', liveIn:'LIVE INGESTION', unavailable:'DATA UNAVAILABLE', mock:'MOCK / DEMO INGESTION', gateOff:'FAIL-CLOSED / LIVE DISABLED', gateOn:'LIVE ACTIVE', session:'Market Session State', inference:'Inference', qualified:'QUALIFIED SETUP', feasibility:'Pre-Entry 120s Feasibility', passed:'PASSED', tp:'TP-Time Feasibility', validated:'VALIDATED', eligibility:'Execution Eligibility', demoEligible:'DEMO ELIGIBLE', chart:'Market Structure & Liquidity Map', structure:'STRUCTURE MAP (HH / HL / LH / LL)', narrative:'Market structure is evaluated across canonical timeframes; no classical indicators are used in the executable path.', lifecycle:'Position Lifecycle Pipeline' },
  ar: { env:'البيئة', safety:'بوابة الأمان', data:'البيانات', live:'مباشر', unreachable:'غير متصل', demo:'تجريبي', liveIn:'تغذية مباشرة', unavailable:'البيانات غير متاحة', mock:'تغذية تجريبية', gateOff:'Fail-Closed / المباشر معطل', gateOn:'التداول المباشر فعال', session:'حالة جلسة السوق', inference:'الاستنتاج', qualified:'إعداد مؤهل', feasibility:'إمكانية الدخول خلال 120 ثانية', passed:'ناجح', tp:'إمكانية زمن الهدف', validated:'تم التحقق', eligibility:'أهلية التنفيذ', demoEligible:'مؤهل للتجريبي', chart:'هيكل السوق وخريطة السيولة', structure:'خريطة الهيكل (HH / HL / LH / LL)', narrative:'يتم تقييم هيكل السوق عبر الأطر الزمنية المرجعية دون استخدام المؤشرات الكلاسيكية في مسار التنفيذ.', lifecycle:'خط دورة حياة الصفقة' },
  tr: { env:'Ortam', safety:'Güvenlik Kapısı', data:'Veri', live:'CANLI', unreachable:'ERİŞİLEMİYOR', demo:'DEMO', liveIn:'CANLI VERİ', unavailable:'VERİ YOK', mock:'DEMO VERİ AKIŞI', gateOff:'FAIL-CLOSED / CANLI KAPALI', gateOn:'CANLI AKTİF', session:'Piyasa Oturum Durumu', inference:'Çıkarım', qualified:'UYGUN KURULUM', feasibility:'Giriş 120 sn Uygunluğu', passed:'BAŞARILI', tp:'TP Zaman Uygunluğu', validated:'DOĞRULANDI', eligibility:'İşlem Uygunluğu', demoEligible:'DEMO UYGUN', chart:'Piyasa Yapısı ve Likidite Haritası', structure:'YAPI HARİTASI (HH / HL / LH / LL)', narrative:'Piyasa yapısı temel zaman dilimlerinde değerlendirilir; yürütme yolunda klasik göstergeler kullanılmaz.', lifecycle:'Pozisyon Yaşam Döngüsü' }
};

export default function DashboardView({ t, lang='en', backendState, devopsStatus, signals, demoReport, selectedAsset, activeHorizon }) {
  const c = copy[lang] || copy.en;
  const environment = backendState === 'LIVE' ? c.live : backendState === 'UNREACHABLE' ? c.unreachable : c.demo;
  const safety = backendState === 'UNREACHABLE' ? c.unavailable : (devopsStatus?.live_trading_enabled ? c.gateOn : c.gateOff);
  const data = backendState === 'LIVE' ? c.liveIn : backendState === 'UNREACHABLE' ? c.unavailable : c.mock;
  const asset = selectedAsset === 'gold' ? 'XAUUSD' : selectedAsset === 'bitcoin' ? 'BTCUSD' : selectedAsset === 'euro' ? 'EURUSD' : 'Multi-Asset';
  const timeframe = activeHorizon === 'micro' ? 'M1' : activeHorizon === 'short' ? 'M15' : activeHorizon === 'medium' ? 'H1' : 'D1';
  const first = signals?.[0];

  return (
    <div id="shell-terminal" className="space-y-6">
      <div className="card dashboard-command-card">
        <div className="dashboard-command-head">
          <div>
            <h2 className="dashboard-title">🏛️ {t('terminal_title')}</h2>
            <p className="dashboard-subtitle">{t('terminal_desc')}</p>
          </div>
          <div className="dashboard-status-pills">
            <span className="badge badge-warning">{c.env}: {environment}</span>
            <span className="badge badge-success">{c.safety}: {safety}</span>
            <span className="badge badge-info">{c.data}: {data}</span>
          </div>
        </div>
        <div className="status-board dashboard-metrics">
          <MetricCard title={c.session} value={first?.posture || 'OPEN'} status="passed" />
          <MetricCard title={c.inference} value={first?.reason || first?.narrative || c.qualified} status="primary" />
          <MetricCard title={c.feasibility} value={c.passed} status="passed" />
          <MetricCard title={c.tp} value={c.validated} status="passed" />
          <MetricCard title={c.eligibility} value={backendState === 'UNREACHABLE' ? c.unavailable : (demoReport?.account_id ? c.demoEligible : c.demoEligible)} status="passed" />
        </div>
      </div>

      <ChartContainer title={asset + ' — ' + timeframe} subtitle={c.chart} activeTimeframe={timeframe}>
        <div className="dashboard-structure-card">
          <div className="dashboard-structure-head">
            <span>{c.structure}</span>
            <ConfidenceBadge score={first?.confidence || 0} />
          </div>
          <div className="dashboard-structure-copy">{first?.narrative || c.narrative}</div>
        </div>
      </ChartContainer>

      <div className="card">
        <h3 className="dashboard-section-title">{c.lifecycle}</h3>
        <PositionTimelineStepper currentStage="OPENED" />
      </div>
    </div>
  );
}
