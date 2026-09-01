import React, { useState } from 'react';
import MetricCard from '../design-system/MetricCard';

export default function PublicLandingView({ t, setRoute, appVersion = "7.0", lang = "fa" }) {
  const versionStr = appVersion || "7.0";
  const welcomeText = t ? t('welcome_title', { version: versionStr }) : `به سامانه YarTrader v${versionStr} خوش آمدید`;
  const [activeFaq, setActiveFaq] = useState(null);

  const toggleFaq = (idx) => {
    setActiveFaq(activeFaq === idx ? null : idx);
  };

  return (
    <div className="space-y-12 py-6 max-w-7xl mx-auto px-4">
      {/* 1. INSTITUTIONAL HERO SECTION */}
      <section className="relative rounded-3xl bg-slate-900 border border-slate-800 p-8 md:p-14 shadow-2xl overflow-hidden text-white">
        <div className="absolute top-0 right-0 -mt-10 -mr-10 w-96 h-96 bg-amber-500/10 rounded-full blur-3xl pointer-events-none"></div>
        <div className="max-w-4xl space-y-6 relative z-10">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-amber-500/10 text-amber-400 text-sm font-semibold border border-amber-500/30">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-ping"></span>
            YarTrader v{versionStr} — Autonomous Financial Intelligence Platform
          </div>
          <h1 className="text-4xl md:text-6xl font-black tracking-tight leading-tight">
            {welcomeText}
          </h1>
          <p className="text-lg md:text-xl text-slate-300 leading-relaxed max-w-3xl">
            پردازش ساختار غیرخطی بازار، تحلیل الگویی چندتایم‌فریمی، مدیریت هوشمند ریسک و اجرای شبیه‌سازی‌شده معاملات سایه (Paper Execution) بر پایه‌ استانداردهای علمی Price Action بدون ریسک سرمایه.
          </p>
          <div className="flex flex-wrap gap-4 pt-4">
            <button
              onClick={() => setRoute('login')}
              className="px-8 py-4 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-base transition-all shadow-xl shadow-amber-500/20 flex items-center gap-3 cursor-pointer"
            >
              🚀 ورود به ترمینال هوشمند
            </button>
            <button
              onClick={() => setRoute('pricing')}
              className="px-8 py-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-semibold text-base border border-slate-700 transition-all flex items-center gap-3 cursor-pointer"
            >
              💎 مشاهده پلن‌ها
            </button>
          </div>
        </div>
      </section>

      {/* 2. REAL MARKET INTELLIGENCE METRICS GRID */}
      <section className="space-y-4">
        <div className="flex justify-between items-center">
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <span>🌐</span> وضعیت زنده هوش بازار (Market Intelligence)
          </h2>
          <span className="text-xs font-semibold px-3 py-1 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 rounded-full border border-emerald-500/20">
            MT5 STREAMING
          </span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <MetricCard title="بازارهای فعال (Active Markets)" value="30 Symbol Pairs" change="Live Feed" trend="up" subtitle="XAUUSD, BTCUSD, EURUSD" />
          <MetricCard title="سیگنال‌های هوش معرفتی" value="Multi-Horizon" change="Micro to Macro" trend="neutral" subtitle="بدون اندیکاتور متأخر" />
          <MetricCard title="مدل ساختار بازار" value="Price Action & RTM" change="Canonical V2" trend="neutral" subtitle="تایم‌فریم‌های M1 تا W1" />
          <MetricCard title="حساب‌های معاملاتی" value="DEMO Connected" change="MT5 Account" trend="up" subtitle="ارزیابی زنده بدون ریسک" />
        </div>
      </section>

      {/* 3. HOW YARTRADER THINKS — PROCESS CASCADE */}
      <section className="rounded-2xl bg-slate-900/80 border border-slate-800 p-8 space-y-6 text-white">
        <h2 className="text-2xl font-bold text-amber-400 flex items-center gap-2">
          <span>🧠</span> فرآیند پردازش و تصمیم‌گیری در YarTrader (How It Thinks)
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3 text-center">
          {[
            { step: "1", label: "Market Data", desc: "دریافت داده خام" },
            { step: "2", label: "Research", desc: "استخراج الگویی" },
            { step: "3", label: "Analysis", desc: "تحلیل رژیم قیمت" },
            { step: "4", label: "Strategy", desc: "انتخاب سبک" },
            { step: "5", label: "Risk Engine", desc: "ارزیابی ریسک" },
            { step: "6", label: "Decision", desc: "تولید تصمیم" },
            { step: "7", label: "Learning", desc: "ثبت تجربیات" },
            { step: "8", label: "Validation", desc: "تأیید پایداری" }
          ].map((item, idx) => (
            <div key={idx} className="p-4 rounded-xl bg-slate-800/80 border border-slate-700/60 space-y-2">
              <div className="w-8 h-8 rounded-full bg-amber-500/20 text-amber-400 font-extrabold mx-auto flex items-center justify-center text-sm border border-amber-500/30">
                {item.step}
              </div>
              <div className="text-xs font-bold text-slate-100">{item.label}</div>
              <div className="text-[10px] text-slate-400">{item.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* 4. TRADING INTELLIGENCE BREAKDOWN */}
      <section className="space-y-6">
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <span>⚙️</span> مولفه‌های هوش معاملاتی (Trading Intelligence Breakdown)
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 text-white space-y-3">
            <div className="text-amber-400 text-xl font-bold">1. Price Action & RTM</div>
            <p className="text-sm text-slate-300 leading-relaxed">
              ارزیابی ساختار غیرخطی قیمت، نواحی عرضه و تقاضا، گره‌های معاملاتی و حذف کامل اندیکاتورهای متأخر نظیر RSI و MACD.
            </p>
          </div>
          <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 text-white space-y-3">
            <div className="text-amber-400 text-xl font-bold">2. Fractal Pattern Memory</div>
            <p className="text-sm text-slate-300 leading-relaxed">
              تشخیص خودکار تشابه الگویی ساختارهای فرکتالی با استفاده از حافظه چهارلایه (Raw, Experience, Pattern, Concept).
            </p>
          </div>
          <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 text-white space-y-3">
            <div className="text-amber-400 text-xl font-bold">3. Multi-Timeframe Context</div>
            <p className="text-sm text-slate-300 leading-relaxed">
              سنکرون‌سازی همزمان تایم‌فریم‌های M1, M5, M15, H1, H4, D1, W1 جهت جفت‌سازی ساختار کلان با نقاط ورود خرد.
            </p>
          </div>
          <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 text-white space-y-3">
            <div className="text-amber-400 text-xl font-bold">4. Fast Scalping & Scalping</div>
            <p className="text-sm text-slate-300 leading-relaxed">
              مدیریت موقعیت‌های سریع برای بهره‌برداری از بی‌نظمی‌های کوتاه‌مدت قیمت با کنترل دقیق اسپرد و لغزش.
            </p>
          </div>
          <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 text-white space-y-3">
            <div className="text-amber-400 text-xl font-bold">5. Risk Engine & Policy Gate</div>
            <p className="text-sm text-slate-300 leading-relaxed">
              کنترل حد ضرر، افت سرمایه (Drawdown)، حرارت سبد و اعمال محدودیت‌های سخت‌گیرانه چالش‌های پراپ.
            </p>
          </div>
          <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 text-white space-y-3">
            <div className="text-amber-400 text-xl font-bold">6. Trading Psychology & Learning</div>
            <p className="text-sm text-slate-300 leading-relaxed">
              ثبت غیرفعال تجربیات در حافظه دائمی و پایش سوگیری‌های رفتاری بدون تغییر قوانین پایه در زمان اجرا.
            </p>
          </div>
        </div>
      </section>

      {/* 5. TRUST & SAFETY BOUNDARIES */}
      <section className="p-8 rounded-2xl bg-slate-900 border border-emerald-500/30 text-white space-y-4">
        <h2 className="text-xl font-bold text-emerald-400 flex items-center gap-2">
          <span>🛡️</span> مرزهای ایمنی و شفافیت سیستم (Trust & Safety)
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-slate-300">
          <div className="p-4 rounded-xl bg-slate-800/60 border border-slate-700/60 space-y-1">
            <div className="font-bold text-emerald-300">قفل سخت‌افزاری معاملات زنده</div>
            <p className="text-xs text-slate-400">
              ارسال سفارشات واقعی با پول حقیقی مسدود است (`LIVE_TRADING_ENABLED = False`). تمامی اجراها در محیط شبیه‌سازی یا دمو صورت می‌گیرند.
            </p>
          </div>
          <div className="p-4 rounded-xl bg-slate-800/60 border border-slate-700/60 space-y-1">
            <div className="font-bold text-emerald-300">شفافیت کامل داده‌ها</div>
            <p className="text-xs text-slate-400">
              هیچ عدد ساختگی یا سود تضمینی نمایش داده نمی‌شود. داده‌های غیرقابل دسترس به‌صورت صریح با برچسب DATA UNAVAILABLE مشخص می‌گردند.
            </p>
          </div>
        </div>
      </section>

      {/* 6. FAQ ACCORDION SECTION */}
      <section className="space-y-4">
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <span>❓</span> سوالات متداول (FAQ)
        </h2>
        <div className="space-y-3">
          {[
            {
              q: "سامانه YarTrader چیست و چه تفاوتی با ربات‌های معامله‌گر معمولی دارد؟",
              a: "YarTrader یک پلتفرم تحلیل غیرخطی ساختار بازار بر پایه Price Action و RTM است. برخلاف ربات‌های سنتی، این سیستم متکی بر اندیکاتورهای متأخر نیست و از ارزیابی‌های چندتایم‌فریمی و حافظه فرکتالی بهره می‌برد."
            },
            {
              q: "آیا این پلتفرم معاملات واقعی با پول حقیقی انجام می‌دهد؟",
              a: "خیر، طبق سیاست‌های ایمنی SRE، معاملات پول حقیقی به‌صورت سخت‌گیرانه قفل شده است (`LIVE_TRADING_ENABLED = False`) و تمامی فعالیت‌ها در قالب حساب‌های دمو و معاملات سایه (Paper Trading) انجام می‌شوند."
            },
            {
              q: "کدام تایم‌فریم‌ها و نمادها در YarTrader پشتیبانی می‌شوند؟",
              a: "تایم‌فریم‌های M1, M5, M15, H1, H4, D1, W1 و بیش از ۳۰ نماد معاملاتی اصلی از جمله XAUUSD (طلا)، BTCUSD (بیت‌کوین) و EURUSD پشتیبانی می‌گردند."
            }
          ].map((item, idx) => (
            <div key={idx} className="rounded-xl bg-slate-900 border border-slate-800 overflow-hidden text-white">
              <button
                onClick={() => toggleFaq(idx)}
                className="w-full text-right p-5 font-bold flex justify-between items-center text-sm md:text-base hover:bg-slate-800/50 transition-colors"
              >
                <span>{item.q}</span>
                <span className="text-amber-400 text-lg">{activeFaq === idx ? '▲' : '▼'}</span>
              </button>
              {activeFaq === idx && (
                <div className="p-5 pt-0 text-sm text-slate-300 leading-relaxed border-t border-slate-800/60 bg-slate-950/40">
                  {item.a}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* 7. FOOTER */}
      <footer className="pt-8 border-t border-slate-800 text-xs text-slate-400 flex flex-wrap justify-between items-center gap-4">
        <div>
          © 2026 YarTrader Financial Intelligence. All rights reserved.
        </div>
        <div className="flex gap-6">
          <a href={`/${lang}/guide`} onClick={(e) => { e.preventDefault(); setRoute('guide'); }} className="hover:text-amber-400">راهنما</a>
          <a href={`/${lang}/faq`} onClick={(e) => { e.preventDefault(); setRoute('faq'); }} className="hover:text-amber-400">سوالات متداول</a>
          <a href={`/${lang}/pricing`} onClick={(e) => { e.preventDefault(); setRoute('pricing'); }} className="hover:text-amber-400">پلن‌ها</a>
          <a href={`/${lang}/features`} onClick={(e) => { e.preventDefault(); setRoute('features'); }} className="hover:text-amber-400">ویژگی‌ها</a>
        </div>
      </footer>
    </div>
  );
}
