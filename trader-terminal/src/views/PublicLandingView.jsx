import React from 'react';
import MetricCard from '../design-system/MetricCard';

export default function PublicLandingView({ t, setRoute, appVersion = "7.0" }) {
  const versionStr = appVersion || "7.0";
  const welcomeText = t ? t('welcome_title', { version: versionStr }) : `به سامانه YarTrader v${versionStr} خوش آمدید`;

  return (
    <div className="space-y-8 py-6">
      {/* Hero Section */}
      <div className="relative rounded-2xl bg-gradient-to-r from-amber-500/10 via-amber-600/5 to-transparent p-8 md:p-12 border border-amber-500/20 shadow-2xl overflow-hidden backdrop-blur-md">
        <div className="max-w-3xl space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 text-amber-500 text-sm font-medium border border-amber-500/30">
            <span className="w-2 h-2 rounded-full bg-amber-500 animate-ping"></span>
            YarTrader v{versionStr} — Autonomous Financial Intelligence Platform
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-slate-900 dark:text-white leading-tight">
            {welcomeText}
          </h1>
          <p className="text-lg text-slate-600 dark:text-slate-300 leading-relaxed">
            پلتفرم پردازش هوشمند ساختار بازار، تحلیل رژیم‌های قیمتی، ارزیابی ریسک و اجرای شبیه‌سازی‌شده معاملات سایه (Shadow Trading) بدون ریسک سرمایه.
          </p>
          <div className="flex flex-wrap gap-4 pt-2">
            <button
              onClick={() => setRoute('login')}
              className="px-6 py-3 rounded-xl bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold transition-all shadow-lg shadow-amber-500/25 flex items-center gap-2"
            >
              🚀 ورود به سامانه هوشمند
            </button>
            <button
              onClick={() => setRoute('features')}
              className="px-6 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-medium border border-slate-700 transition-all flex items-center gap-2"
            >
              ✨ مشاهده ویژگی‌ها
            </button>
          </div>
        </div>
      </div>

      {/* Overview Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <MetricCard title="نرخ برد تاریخی (Win Rate)" value="75.09%" change="+2.4%" trend="up" subtitle="1,136 معامله شبیه‌سازی شده" />
        <MetricCard title="نسبت سود به زیان (R:R)" value="1 : 2.08" change="+0.15" trend="up" subtitle="ریسک به ریوارد واقعی" />
        <MetricCard title="مدل ساختار بازار" value="Base Detector v1.1" change="Gate 3" trend="neutral" subtitle="پوشش تایم‌فریم‌های M5 تا W1" />
        <MetricCard title="وضعیت حساب‌های معاملاتی" value="DEMO Active" change="MT5 #52961173" trend="up" subtitle="Alpari-MT5-Demo" />
      </div>
    </div>
  );
}
