import React from 'react';
import MetricCard from '../design-system/MetricCard';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';

export default function PublicLandingView({
  t,
  lang,
  navigateTo,
  appVersion,
  publicMetrics,
  compounding,
  setCompounding,
  runCompoundingSimulation
}) {
  return (
    <div className="space-y-12 py-6 max-w-7xl mx-auto px-4">
      {/* Hero Banner Section */}
      <section className="relative rounded-3xl bg-[var(--surface-dark)] border border-[var(--border-dark)] p-8 md:p-14 shadow-2xl overflow-hidden text-[var(--text-dark)]">
        <div className="absolute top-0 right-0 -mt-10 -mr-10 w-96 h-96 bg-[var(--primary)]/10 rounded-full blur-3xl pointer-events-none"></div>
        <div className="max-w-4xl space-y-6 relative z-10">
          <div className="inline-flex items-center gap-2">
            <Badge variant="warning">
              <span className="w-2.5 h-2.5 rounded-full bg-[var(--primary)] animate-ping inline-block mr-1"></span>
              {t('welcome_title', { version: appVersion || '7.0.0' })}
            </Badge>
          </div>

          <h1 className="text-4xl md:text-6xl font-black tracking-tight leading-tight">
            {lang === 'fa' ? 'پلتفرم هوش مالی و تحلیل ساختار غیرخطی بازار' : 'Autonomous Financial Intelligence & Non-Linear Market Structure Platform'}
          </h1>

          <p className="text-lg md:text-xl text-[var(--text-muted)] leading-relaxed max-w-3xl">
            {t('welcome_desc')}
          </p>

          <div className="flex flex-wrap gap-4 pt-4">
            <Button
              variant="primary"
              size="lg"
              onClick={() => navigateTo('/register')}
            >
              🚀 {t('nav_register')}
            </Button>
            <Button
              variant="secondary"
              size="lg"
              onClick={() => navigateTo('/features')}
            >
              📖 {t('nav_features')}
            </Button>
          </div>
        </div>
      </section>

      {/* Platform Live Metrics Board */}
      <section className="space-y-4">
        <div className="flex justify-between items-center">
          <h2 className="text-2xl font-bold text-[var(--primary)] flex items-center gap-2">
            📊 {t('portal_status')}
          </h2>
          <Badge variant="passed">{t('pes_compliant')}</Badge>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <MetricCard
            title={t('pub_markets_title')}
            value={publicMetrics?.activeMarketsCount || '30'}
            status="passed"
          />
          <MetricCard
            title={t('pub_trades_title')}
            value={publicMetrics?.historicalSimulatedTrades || '125.4k+'}
            status="primary"
          />
          <MetricCard
            title={t('pub_uptime_title')}
            value={publicMetrics?.platformUptimePct ? `${publicMetrics.platformUptimePct}%` : '99.9%'}
            status="passed"
          />
          <MetricCard
            title={t('pub_standards_title')}
            value={t('pes_compliant')}
            status="warn"
          />
        </div>
      </section>

      {/* 8 Canonical Timeframe Architecture */}
      <Card>
        <CardHeader>
          <CardTitle>
            🕒 {lang === 'fa' ? 'معماری هشت‌گانه تایم‌فریم‌های فرکتالی' : '8 Canonical Fractal Timeframe Horizons'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3 text-center">
            {[
              { tf: '1 Tick Frame', label: 'Micro Scalp', desc: 'M1 Execution' },
              { tf: '4 Tick Frame', label: 'M5 Structure', desc: 'Fast Trigger' },
              { tf: '16 Tick Frame', label: 'M15 Intraday', desc: 'Short Horizon' },
              { tf: '64 Tick Frame', label: 'H1 Primary', desc: 'Medium Horizon' },
              { tf: '256 Tick Frame', label: 'H4 Trend', desc: 'Macro Regime' },
              { tf: '1024 Tick Frame', label: 'D1 Structural', desc: 'Daily Bias' },
              { tf: '4096 Tick Frame', label: 'W1 Institutional', desc: 'Weekly Framework' },
              { tf: '16384 Tick Frame', label: 'MN Macro Anchor', desc: 'Cycle Regime' }
            ].map((item, idx) => (
              <div key={idx} className="p-3 rounded-xl bg-[var(--surface-light)] border border-[var(--border-dark)] space-y-1">
                <Badge variant="primary" className="mx-auto mb-1">{idx + 1}</Badge>
                <div className="text-xs font-bold text-[var(--text-dark)]">{item.label}</div>
                <div className="text-[10px] text-[var(--text-muted)]">{item.desc}</div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Core Technical Capabilities Grid */}
      <section className="space-y-6">
        <h2 className="text-2xl font-bold text-[var(--primary)] flex items-center gap-2">
          ⚡ {t('nav_features')}
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>1. Price Action & RTM</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-[var(--text-muted)] leading-relaxed">
                {t('feature_1_desc')}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>2. RangeRegimeEngine (7 Regimes)</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-[var(--text-muted)] leading-relaxed">
                {t('feature_2_desc')}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>3. SRE Risk Engine & 8% Kill Switch</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-[var(--text-muted)] leading-relaxed">
                {t('feature_3_desc')}
              </p>
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  );
}
