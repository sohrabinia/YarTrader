import React from 'react';
import MetricCard from '../design-system/MetricCard';

export default function PublicLandingView({ t, setRoute }) {
  return (
    <div className="space-y-8 py-6">
      {/* Hero Section */}
      <div className="relative rounded-2xl bg-gradient-to-r from-amber-500/10 via-amber-600/5 to-transparent p-8 md:p-12 border border-amber-500/20 shadow-2xl overflow-hidden backdrop-blur-md">
        <div className="max-w-3xl space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 text-amber-500 text-sm font-medium border border-amber-500/30">
            <span className="w-2 h-2 rounded-full bg-amber-500 animate-ping"></span>
            YarTrader Autonomous Financial Intelligence Platform
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-slate-900 dark:text-white leading-tight">
            سامانه خودکار و هوشمند مدیریت معاملات مالی و تحلیل فرکتال
          </h1>
          <p className="text-lg text-slate-600 dark:text-slate-300 leading-relaxed">
            پلتفرم پردازش هوشمند ساختار بازار، تحلیل رژیم‌های قیمتی، ارزیابی ریسک و مدیریت طول عمر پوزیشن‌های فرکتال بدون معامله واقعی با پول حقیقی.
          </p>

          {/* Scientific Release Status Badge Grid */}
          <div className="flex flex-wrap gap-2 pt-2 text-xs font-bold">
            <span className="px-3 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              IMPLEMENTATION = PASS
            </span>
            <span className="px-3 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              SCIENTIFIC VALIDATION = PASS
            </span>
            <span className="px-3 py-1 rounded bg-red-500/10 text-red-400 border border-red-500/30">
              PROFITABILITY = NOT ESTABLISHED / FAIL
            </span>
            <span className="px-3 py-1 rounded bg-red-500/10 text-red-400 border border-red-500/30">
              LIVE TRADING = DISABLED
            </span>
            <span className="px-3 py-1 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
              RELEASE READY = NO
            </span>
          </div>

          <div className="flex flex-wrap gap-4 pt-2">
            <button
              onClick={() => setRoute ? setRoute('login') : window.location.hash = '#/login'}
              className="px-6 py-3 rounded-xl bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold transition-all shadow-lg shadow-amber-500/25 flex items-center gap-2"
            >
              🚀 ورود به سامانه هوشمند
            </button>
            <button
              onClick={() => setRoute ? setRoute('features') : window.location.hash = '#/features'}
              className="px-6 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-medium border border-slate-700 transition-all flex items-center gap-2"
            >
              ✨ مشاهده ویژگی‌ها و گزارش علمی
            </button>
          </div>
        </div>
      </div>

      {/* Verified Overview Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <MetricCard title="نرخ برد خودکار (Win Rate)" value="30.73%" status="failed" subtitle="500 فرصت ارزیابی‌شده (2021–2026)" />
        <MetricCard title="امید ریاضی (Expectancy)" value="-$4.60 / trade" status="failed" subtitle="سودآوری هنوز اثبات نشده است" />
        <MetricCard title="ضریب سودآوری (Profit Factor)" value="0.86" status="failed" subtitle="Net P&L: -$2,066.52" />
        <MetricCard title="وضعیت حساب‌های معاملاتی" value="DEMO / Paper" status="passed" subtitle="معاملات واقعی کاملاً مسدود است" />
      </div>

      {/* AEO & BEO Structured FAQ Section */}
      <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-8 space-y-6">
        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
          <span>❓</span> سوالات متداول و پاسخ‌های مبتنی بر واقعیت (FAQ / AEO & BEO)
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm text-slate-300">
          <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800 space-y-2">
            <h3 className="font-bold text-amber-400 text-base">۱. پلتفرم YarTrader چیست و چه کاربردی دارد؟</h3>
            <p className="leading-relaxed text-slate-400">
              یارتریدر یک سامانه خودکار و هوشمند تحقیق و پایش ساختار فرکتالی بازار است که با شناسایی نواحی Base، Expansion، Leg و Return امکان تحلیل چندتایم‌فریمی قیمت را فراهم می‌سازد.
            </p>
          </div>
          <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800 space-y-2">
            <h3 className="font-bold text-amber-400 text-base">۲. آیا YarTrader معاملات واقعی با پول حقیقی انجام می‌دهد؟</h3>
            <p className="leading-relaxed text-slate-400">
              خیر. اجرای معاملات واقعی با پول حقیقی (Live Trading) در تمام بخش‌های سامانه به طور کامل مسدود و غیرفعال است (LIVE_TRADING_ENABLED=False). کلیه فعالیت‌ها صرفاً در محیط‌های شبیه‌سازی و حساب دمو انجام می‌شوند.
            </p>
          </div>
          <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800 space-y-2">
            <h3 className="font-bold text-amber-400 text-base">۳. پایش ریسک چالش‌های پراپ (Prop Firm Challenge) چگونه کار می‌کند؟</h3>
            <p className="leading-relaxed text-slate-400">
              موتور پایش پراپ حد ضرر روزانه، حداکثر افت سرمایه (Drawdown) و حجم پوزیشن‌ها را مطابق با قوانین چالش پایش می‌کند، بدون آن‌که وعده قبولی تضمینی یا سودآوری قطعی ارائه دهد.
            </p>
          </div>
          <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800 space-y-2">
            <h3 className="font-bold text-amber-400 text-base">۴. پلتفرم بر روی چه نمادها و تایم‌فریم‌هایی عمل می‌کند؟</h3>
            <p className="leading-relaxed text-slate-400">
              تمرکز اصلی سامانه بر روی طلا (XAUUSD)، بیت‌کوین (BTCUSD) و یورو/دلار (EURUSD) در تایم‌فریم‌های ماهانه تا ۱ دقیقه با تایم‌فریم‌های فرکتالی توان ۲ و ۳ است.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
