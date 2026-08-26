import React from 'react';

export default function GuideView({ lang, t }) {
  const isFa = lang === 'fa';
  const isAr = lang === 'ar';
  const isTr = lang === 'tr';

  return (
    <div id="shell-guide" className="card" style={{ borderTop: '4px solid var(--primary)' }}>
      <h2 style={{ marginTop: 0, color: 'var(--primary)' }}>
        📚 {t('guide_title') || (isFa ? 'راهنمای جامع پلتفرم هوش مالی YarTrader' : isTr ? 'YarTrader Platform Rehberi' : isAr ? 'دليل منصة YarTrader الشامل' : 'YarTrader Platform Comprehensive Guide')}
      </h2>
      <p style={{ color: 'var(--text-muted)', marginBottom: '25px', lineHeight: '1.7' }}>
        {t('guide_subtitle') || (isFa ? 'آموزش گام‌به‌گام کارکرد پلتفرم، حالت‌های معاملاتی، مدیریت ریسک چالش پراپ و ساختارهای غیرخطی فرکتالی.' : 'Step-by-step guide to platform architecture, trading modes, risk management, and multi-scale fractal intelligence.')}
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px', marginBottom: '30px' }}>
        <div className="status-item" style={{ textAlign: 'inherit', padding: '20px', borderLeft: '4px solid var(--primary)' }}>
          <h3 style={{ color: 'var(--primary)', marginTop: 0 }}>
            1. {isFa ? 'معرفی پلتفرم YarTrader' : isTr ? '1. YarTrader Platformuna Giriş' : isAr ? '1. مقدمة عن منصة YarTrader' : '1. What is YarTrader?'}
          </h3>
          <p style={{ fontSize: '0.9em', lineHeight: '1.6', color: 'var(--text-dark)' }}>
            {isFa
              ? 'پلتفرم YarTrader یک سامانه هوش مالی خودکار برای تحلیل ساختارهای قیمت و مدیریت ریسک است. این پلتفرم کارگزار نیست و وجوه کاربران را نگهداری نمی‌کند.'
              : 'YarTrader is an autonomous financial intelligence platform for structural price analysis and risk management. It is NOT a broker and does not hold user funds.'}
          </p>
        </div>

        <div className="status-item" style={{ textAlign: 'inherit', padding: '20px', borderLeft: '4px solid var(--accent)' }}>
          <h3 style={{ color: 'var(--accent)', marginTop: 0 }}>
            2. {isFa ? 'حالت‌های چهارگانه پلتفرم' : isTr ? '2. Dört İşlem Modu' : isAr ? '2. الأنماط الأربعة للتداول' : '2. Four Platform Modes'}
          </h3>
          <ul style={{ fontSize: '0.85em', lineHeight: '1.8', color: 'var(--text-dark)', paddingLeft: '15px' }}>
            <li><strong>Backtest:</strong> {isFa ? 'شبیه‌سازی تاریخچه گذشته بدون ریسک' : 'Historical market simulations'}</li>
            <li><strong>Demo:</strong> {isFa ? 'معاملات آزمایشی در سرور آلپاری (#52961173)' : 'Simulated broker demo execution'}</li>
            <li><strong>Shadow (Paper):</strong> {isFa ? 'رهگیری پوزیشن‌های مجازی در حساب سایه' : 'Virtual shadow trade journaling'}</li>
            <li><strong>Live Mode:</strong> <span style={{ color: 'var(--danger)' }}>{isFa ? 'قفل ایمنی غیرفعال (LIVE_TRADING_ENABLED=False)' : 'HARD BLOCKED (LIVE_TRADING_ENABLED=False)'}</span></li>
          </ul>
        </div>

        <div className="status-item" style={{ textAlign: 'inherit', padding: '20px', borderLeft: '4px solid var(--primary)' }}>
          <h3 style={{ color: 'var(--primary)', marginTop: 0 }}>
            3. {isFa ? 'مدیریت ریسک چالش پراپ (Prop Firm)' : isTr ? '3. Prop Firm Risk Yönetimi' : isAr ? '3. إدارة مخاطر تحديات شركات التداول' : '3. Prop Firm Challenge Risk Controls'}
          </h3>
          <p style={{ fontSize: '0.9em', lineHeight: '1.6', color: 'var(--text-dark)' }}>
            {isFa
              ? 'تنظیم سقف ضرر روزانه، حداکثر افت سرمایه (Drawdown) و حجم پوزیشن‌ها به همراه هشدار قبل از رسیدن به آستانه خطر. سیستم هیچ‌گونه تضمین قبولی یا سود ارائه نمی‌دهد.'
              : 'Configurable daily loss limits, drawdown protection boundaries, and position sizing gates with risk alerts. Strictly does NOT guarantee passing or profits.'}
          </p>
        </div>

        <div className="status-item" style={{ textAlign: 'inherit', padding: '20px', borderLeft: '4px solid var(--accent)' }}>
          <h3 style={{ color: 'var(--accent)', marginTop: 0 }}>
            4. {isFa ? 'هوش فرکتالی و ماتریس یادگیری' : isTr ? '4. Fraktal Zeka ve Öğrenme' : isAr ? '4. الذكاء التكراري ومصفوفة التعلم' : '4. Fractal Intelligence & Learning Matrix'}
          </h3>
          <p style={{ fontSize: '0.9em', lineHeight: '1.6', color: 'var(--text-dark)' }}>
            {isFa
              ? 'شناسایی بیس‌های ساختاری بدون اندیکاتورهای کلاسیک در افق‌های زمانی متداخل (MN1 تا M1) به همراه ارزیابی MFE/MAE و عدم تغییر پارامترها در زمان بازار.'
              : 'Indicator-free structural base detection across multi-timeframe scales (MN1 to M1) with post-trade outcome analysis and strict sample-size guards.'}
          </p>
        </div>
      </div>

      <div style={{ padding: '15px', background: 'rgba(255, 255, 255, 0.03)', borderRadius: '8px', fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: '1.6' }}>
        🛡️ <strong>{isFa ? 'سلب مسئولیت ایمنی:' : 'Safety Disclaimer:'}</strong> {isFa ? 'نتایج شبیه‌سازی گذشته یا حساب‌های آزمایشی تضمین‌کننده عملکرد آینده نیستند. کلیه قابلیت‌ها تحت گیت‌های ایمنی SRE اجرا می‌شوند.' : 'Simulated or demo results do not guarantee future performance. All capabilities run under strict SRE safety gates.'}
      </div>
    </div>
  );
}
