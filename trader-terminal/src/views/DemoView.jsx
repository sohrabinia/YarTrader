import React from 'react';
import MetricCard from '../design-system/MetricCard';
import StatusBadge from '../design-system/StatusBadge';
import DataTable from '../design-system/DataTable';

const copy={
 fa:{title:'مرکز اجرای آزمایشی MT5',desc:'وضعیت اجرای DEMO و داده‌های واقعی حساب متصل؛ بدون مسیر اجرای LIVE.',account:'شماره حساب دمو',balance:'موجودی حساب',validation:'اعتبارسنجی نشست و TP',liveLock:'قفل معاملات واقعی',history:'تاریخچه اجرای DEMO',unavailable:'داده در دسترس نیست',disabled:'غیرفعال',active:'DEMO فعال'},
 en:{title:'MT5 Demo Execution Center',desc:'Authoritative DEMO execution state for the connected account; no LIVE execution path.',account:'Demo Account',balance:'Account Balance',validation:'Session & TP Validation',liveLock:'Live Trading Safety Gate',history:'DEMO Execution History',unavailable:'DATA UNAVAILABLE',disabled:'DISABLED',active:'DEMO ACTIVE'},
 ar:{title:'مركز تنفيذ MT5 التجريبي',desc:'الحالة الفعلية لتنفيذ DEMO للحساب المتصل؛ لا يوجد مسار لتنفيذ التداول المباشر.',account:'حساب DEMO',balance:'رصيد الحساب',validation:'التحقق من الجلسة والهدف',liveLock:'بوابة أمان التداول المباشر',history:'سجل تنفيذ DEMO',unavailable:'البيانات غير متاحة',disabled:'معطل',active:'DEMO فعال'},
 tr:{title:'MT5 Demo İşlem Merkezi',desc:'Bağlı hesabın gerçek DEMO yürütme durumu; CANLI işlem yolu bulunmaz.',account:'Demo Hesabı',balance:'Hesap Bakiyesi',validation:'Oturum ve TP Doğrulaması',liveLock:'Canlı İşlem Güvenlik Kapısı',history:'DEMO İşlem Geçmişi',unavailable:'VERİ YOK',disabled:'KAPALI',active:'DEMO AKTİF'}
};

export default function DemoView({ lang='en', demoReport }) {
 const c=copy[lang]||copy.en;
 const report=demoReport||{};
 const balance=report.balance ?? report.account_balance;
 const trades=Array.isArray(report.trades)?report.trades:[];
 const rows=trades.map(x=>[x.ticket||x.order_id||'—',x.symbol||'—',x.type||x.direction||'—',x.volume??'—',x.sl??'—',x.tp??'—',x.profit??x.pnl??'—']);
 return <div id="shell-demo" className="space-y-6">
  <div className="card demo-hero"><div><h2 className="demo-title">🎮 {c.title}</h2><p>{c.desc}</p></div><StatusBadge status={c.active} type="passed" /></div>
  <div className="status-board">
   <MetricCard title={c.account} value={report.account_id || c.unavailable} status="passed" subtitle={report.broker || 'MT5 Demo'} />
   <MetricCard title={c.balance} value={balance != null ? '$'+Number(balance).toLocaleString() : c.unavailable} status="passed" />
   <MetricCard title={c.validation} value={report.validation_status || c.unavailable} status="passed" />
   <MetricCard title={c.liveLock} value={report.live_trading_enabled ? 'LIVE ENABLED' : c.disabled} status="primary" />
  </div>
  <div className="card"><h3 className="demo-section-title">{c.history}</h3>
   <DataTable headers={['Ticket #','Symbol','Type','Lots','Stop Loss','Take Profit','P&L']} rows={rows} emptyMessage={c.unavailable}/>
  </div>
 </div>;
}
