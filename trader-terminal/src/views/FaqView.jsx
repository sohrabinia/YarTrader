import React from 'react';

export default function FaqView({ lang, t }) {
  const isFa = lang === 'fa';
  const isAr = lang === 'ar';
  const isTr = lang === 'tr';

  const faqItems = [
    {
      q: isFa ? 'پلتفرم YarTrader چیست؟' : isTr ? 'YarTrader Nedir?' : isAr ? 'ما هي منصة YarTrader؟' : 'What is YarTrader?',
      a: isFa
        ? 'پلتفرم YarTrader یک سامانه هوش مالی خودکار برای تحلیل ساختارهای غیرخطی قیمت و مدیریت ریسک معامله‌گران است.'
        : 'YarTrader is an autonomous financial intelligence platform for non-linear price structure analysis and risk management.'
    },
    {
      q: isFa ? 'آیا YarTrader یک کارگزار (Broker) است؟' : isTr ? 'YarTrader Bir Broker Mıdır?' : isAr ? 'هل YarTrader شركة وساطة؟' : 'Is YarTrader a Broker?',
      a: isFa
        ? 'خیر، YarTrader کارگزار نیست و هیچ‌گونه سپرده مالی یا وجه سرمایه‌گذاران را نگهداری نمی‌کند.'
        : 'No, YarTrader is not a broker and does not hold user deposits or investor funds.'
    },
    {
      q: isFa ? 'آیا YarTrader کسب سود را تضمین می‌کند؟' : isTr ? 'YarTrader Kar Garantisi Verir Mi?' : isAr ? 'هل تضمن YarTrader الأرباح؟' : 'Does YarTrader Guarantee Profit?',
      a: isFa
        ? 'خیر، بر اساس قوانین مدیریت ریسک و تعهدات اخلاقی، هیچ‌گونه تضمین سود یا قبولی در چالش‌های پراپ ارائه نمی‌شود.'
        : 'No. Strictly no profit or prop challenge passing guarantees are promised or implied.'
    },
    {
      q: isFa ? 'تفاوت حالت‌های Backtest و Demo چیست؟' : isTr ? 'Backtest ve Demo Mod Farkı Nedir?' : isAr ? 'ما الفرق بين Backtest و Demo؟' : 'What is the Difference Between Backtest and Demo Modes?',
      a: isFa
        ? 'حالت Backtest شبیه‌سازی تاریخچه گذشته بازار است، در حالی که Demo اجرای آزمایشی سفارشات زنده روی سرور متاتریدر ۵ بدون ریسک مالی می‌باشد.'
        : 'Backtest runs historical simulation on past market feeds, while Demo executes orders on live MT5 demo accounts with zero financial risk.'
    },
    {
      q: isFa ? 'چرا در برخی مواقع هیچ سیگنال فعالی وجود ندارد؟' : isTr ? 'Neden Bazen Sinyal Bulunmaz؟' : isAr ? 'لماذا لا توجد إشارات أحياناً؟' : 'Why Can There Be No Valid Signals?',
      a: isFa
        ? 'زیرا کلیه کندل‌ها و موقعیت‌ها از ۳ گیت پالایش کلان (Macro)، ساختاری (Structural) و ریسک (Risk) عبور می‌کنند. اگر چیدمانی از هر سه گیت عبور نکند، جهت سیگنال WAIT اعلام می‌شود.'
        : 'Because candidates pass through strict Macro, Structural, and Risk qualification gates. If no setup passes all three, direction remains WAIT.'
    },
    {
      q: isFa ? 'پلن چالش پراپ (Prop Firm Challenge Plan) چگونه کار می‌کند؟' : isTr ? 'Prop Challenge Plan Nasıl Çalışır?' : isAr ? 'كيف تعمل خطة تحدي شركات التداول؟' : 'How Does the Prop Firm Challenge Plan Work?',
      a: isFa
        ? 'این پلن به معامله‌گر اجازه می‌دهد قوانین شرکت پراپ (حد ضرر روزانه، حداکثر افت سرمایه، حجم پوزیشن) را تعریف و هشدارهای زنده ریسک دریافت کند.'
        : 'It allows traders to configure firm evaluation rules (daily loss limit, max drawdown, exposure) and receive live risk compliance alerts.'
    },
    {
      q: isFa ? 'چگونه داده‌های بازار و وضعیت سیستم پایش می‌شوند؟' : isTr ? 'Sistem Durumu Nasıl İzlenir?' : isAr ? 'كيف يتم مراقبة حالة النظام؟' : 'How is System Status Monitored?',
      a: isFa
        ? 'از طریق بخش SRE Console و تب‌های آنلاین Ingestion، MT5 Stream و APES Compliance در مسیر /admin.'
        : 'Via SRE Console monitoring live Ingestion, MT5 Stream, and APES Compliance status in the /admin dashboard.'
    }
  ];

  return (
    <div id="shell-faq" className="card" style={{ borderTop: '4px solid var(--accent)' }}>
      <h2 style={{ marginTop: 0, color: 'var(--primary)' }}>
        ❓ {t('faq_title') || (isFa ? 'سوالات متداول (FAQ)' : isTr ? 'Sıkça Sorulan Sorular' : isAr ? 'الأسئلة الشائعة' : 'Frequently Asked Questions')}
      </h2>
      <p style={{ color: 'var(--text-muted)', marginBottom: '25px', lineHeight: '1.6' }}>
        {t('faq_subtitle') || (isFa ? 'پاسخ به رایج‌ترین پرسش‌های کاربران درباره کارکرد پلتفرم، مدیریت ریسک، حالت‌های معاملاتی و چالش پراپ.' : 'Answers to common questions regarding platform capabilities, risk limits, trading modes, and prop rules.')}
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
        {faqItems.map((item, idx) => (
          <div
            key={idx}
            className="status-item"
            style={{
              padding: '18px',
              borderLeft: '4px solid var(--primary)',
              transition: 'all 0.2s',
              textAlign: 'inherit'
            }}
          >
            <div style={{ fontWeight: 'bold', color: 'var(--primary)' }}>
              <span>{item.q}</span>
            </div>
            <div style={{ marginTop: '12px', fontSize: '0.9em', color: 'var(--text-muted)', lineHeight: '1.7', borderTop: '1px solid var(--border-dark)', paddingTop: '10px' }}>
              {item.a}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
