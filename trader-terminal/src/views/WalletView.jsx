import React, { useEffect, useState } from 'react';
import { apiService } from '../services/api.js';

export default function WalletView({ lang = 'en' }) {
  const [wallet, setWallet] = useState(null);
  const [deposits, setDeposits] = useState([]);
  const [form, setForm] = useState({ network: 'TON', tx_hash: '', amount_usdt: '' });
  const [submitMsg, setSubmitMsg] = useState('');
  const [copied, setCopied] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const rtl = lang === 'fa' || lang === 'ar';

  const txLinks = {
    TON: 'https://tonviewer.com/',
    TRC20: 'https://tronscan.org/',
    ERC20: 'https://etherscan.io/',
    BEP20: 'https://bscscan.com/',
    SOLANA: 'https://solscan.io/'
  };

  const t = {
    fa: {
      title: 'کیف پول دریافت USDT', sub: 'فقط دریافت — برداشت و ارسال از YarTrader فعال نیست.',
      empty: 'هنوز آدرس دریافت برای شبکه‌ای پیکربندی نشده است.', copy: 'کپی آدرس', copied: 'آدرس کپی شد',
      network: 'شبکه', warning: 'قبل از واریز، شبکه را دقیقاً با شبکه انتخابی فرستنده تطبیق دهید.',
      confirm: 'ثبت واریز', confirmHelp: 'پس از ارسال USDT، هش تراکنش را ثبت کنید. اعتبار فقط پس از تأیید مدیر به دفترکل اضافه می‌شود.',
      tx: 'هش تراکنش', amount: 'مقدار USDT', submit: 'ثبت واریز', submitted: 'واریز برای بررسی ثبت شد.',
      history: 'تاریخچه واریز', receiveOnly: 'فقط دریافت', explorer: 'اکسپلورر', loading: 'در حال بارگذاری…',
      failed: 'ثبت واریز ناموفق بود.'
    },
    ar: {
      title: 'محفظة استلام USDT', sub: 'استلام فقط — السحب والإرسال من YarTrader غير متاحين.',
      empty: 'لم يتم إعداد عنوان استلام لأي شبكة بعد.', copy: 'نسخ العنوان', copied: 'تم نسخ العنوان',
      network: 'الشبكة', warning: 'طابق الشبكة بدقة قبل الإيداع.',
      confirm: 'تأكيد الإيداع', confirmHelp: 'بعد إرسال USDT، أرسل معرّف المعاملة. تتم إضافة الرصيد إلى دفتر الأستاذ بعد مراجعة المسؤول فقط.',
      tx: 'معرّف المعاملة', amount: 'مبلغ USDT', submit: 'إرسال الإيداع', submitted: 'تم إرسال الإيداع للمراجعة.',
      history: 'سجل الإيداعات', receiveOnly: 'استلام فقط', explorer: 'المستكشف', loading: 'جارٍ التحميل…',
      failed: 'فشل إرسال الإيداع.'
    },
    tr: {
      title: 'USDT Alma Cüzdanı', sub: 'Yalnızca alma — YarTrader üzerinden çekim veya gönderim yoktur.',
      empty: 'Henüz hiçbir ağ için alım adresi yapılandırılmadı.', copy: 'Adresi kopyala', copied: 'Adres kopyalandı',
      network: 'Ağ', warning: 'Yatırmadan önce gönderici ağını tam olarak eşleştirin.',
      confirm: 'Yatırma bildirimi', confirmHelp: 'USDT gönderdikten sonra işlem hash bilgisini bildirin. Bakiye yalnızca yönetici onayından sonra deftere eklenir.',
      tx: 'İşlem hash', amount: 'USDT tutarı', submit: 'Yatırmayı gönder', submitted: 'Yatırma incelemeye gönderildi.',
      history: 'Yatırma geçmişi', receiveOnly: 'YALNIZCA ALMA', explorer: 'Gezgin', loading: 'Yükleniyor…',
      failed: 'Yatırma gönderilemedi.'
    },
    en: {
      title: 'USDT Receive Wallet', sub: 'Receive only — withdrawals and outbound transfers are disabled.',
      empty: 'No receive address has been configured yet.', copy: 'Copy address', copied: 'Address copied',
      network: 'Network', warning: 'Match the sender network exactly before depositing.',
      confirm: 'Deposit confirmation', confirmHelp: 'After sending USDT, submit the transaction hash. Credit is added to the ledger only after administrative verification.',
      tx: 'Transaction hash', amount: 'USDT amount', submit: 'Submit deposit', submitted: 'Deposit submitted for verification.',
      history: 'Deposit history', receiveOnly: 'RECEIVE ONLY', explorer: 'Explorer', loading: 'Loading…',
      failed: 'Submission failed.'
    }
  }[lang] || null;

  useEffect(() => {
    Promise.all([
      apiService.get('/api/user/wallet/receive'),
      apiService.get('/api/user/wallet/deposits')
    ])
      .then(([walletData, depositData]) => {
        setWallet(walletData);
        setDeposits(depositData?.deposits || []);
      })
      .catch(e => setError(e.message || 'Unable to load wallet.'))
      .finally(() => setLoading(false));
  }, []);

  const copy = async (address) => {
    try {
      await navigator.clipboard.writeText(address);
      setCopied(address);
      setTimeout(() => setCopied(''), 1800);
    } catch (_) {
      setCopied('');
    }
  };

  const submit = async () => {
    setSubmitMsg('');
    try {
      const r = await apiService.post('/api/user/wallet/deposits', form);
      setDeposits(prev => [r, ...prev]);
      setForm(prev => ({ ...prev, tx_hash: '', amount_usdt: '' }));
      setSubmitMsg(t.submitted);
    } catch (e) {
      setSubmitMsg(e.message || t.failed);
    }
  };

  if (loading) return <div className="card"><h2>{t.title}</h2><p>{t.loading}</p></div>;
  if (error) return <div className="card" dir={rtl ? 'rtl' : 'ltr'}><h2>{t.title}</h2><div className="status-warn">{error}</div></div>;

  const networks = wallet?.networks || [];
  return (
    <div className="card" dir={rtl ? 'rtl' : 'ltr'} style={{ maxWidth: '980px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'flex-start', flexWrap: 'wrap' }}>
        <div><h2 style={{ marginTop: 0 }}>{t.title}</h2><p style={{ color: 'var(--text-muted)' }}>{t.sub}</p></div>
        <span className="status-passed">{t.receiveOnly}</span>
      </div>

      <div style={{ padding: '12px 14px', border: '1px solid var(--border-dark)', borderRadius: 8, margin: '18px 0', color: 'var(--text-muted)' }}>
        ⚠️ {t.warning}
      </div>

      <div style={{ marginTop: 24, padding: 18, border: '1px solid var(--border-dark)', borderRadius: 10 }}>
        <h3 style={{ marginTop: 0 }}>{t.confirm}</h3>
        <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>{t.confirmHelp}</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 10 }}>
          <select className="form-input" value={form.network} onChange={e => setForm({ ...form, network: e.target.value })}>
            {['TON', 'TRC20', 'ERC20', 'BEP20', 'SOLANA'].map(n => <option key={n}>{n}</option>)}
          </select>
          <input className="form-input" placeholder={t.tx} value={form.tx_hash} onChange={e => setForm({ ...form, tx_hash: e.target.value })} />
          <input className="form-input" type="number" min="0" step="0.000001" placeholder={t.amount} value={form.amount_usdt} onChange={e => setForm({ ...form, amount_usdt: e.target.value })} />
          <button className="btn" disabled={!form.tx_hash.trim() || !form.amount_usdt || Number(form.amount_usdt) <= 0} onClick={submit}>{t.submit}</button>
        </div>
        {submitMsg && <div style={{ marginTop: 10, color: 'var(--text-muted)' }}>{submitMsg}</div>}
      </div>

      {deposits.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <h3>{t.history}</h3>
          {deposits.map(d => (
            <div key={d.deposit_id} style={{ padding: '12px 0', borderBottom: '1px solid var(--border-dark)' }}>
              <strong>{d.amount_usdt} USDT</strong> · {d.network} · {d.status}
              <div style={{ fontSize: 12, color: 'var(--text-muted)', wordBreak: 'break-all' }}>{d.tx_hash}</div>
            </div>
          ))}
        </div>
      )}

      {networks.length === 0 ? (
        <div style={{ padding: '35px 10px', textAlign: 'center', color: 'var(--text-muted)' }}>{t.empty}</div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(300px,1fr))', gap: 16, marginTop: 24 }}>
          {networks.map(n => (
            <div key={n.network} style={{ border: '1px solid var(--border-dark)', borderRadius: 10, padding: 18 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <strong>{n.label || n.network}</strong><span className="status-passed">{n.network}</span>
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>{t.network}: {n.network} · USDT</div>
              <code style={{ display: 'block', wordBreak: 'break-all', padding: 12, background: 'rgba(15,23,42,.45)', borderRadius: 6 }}>{n.address}</code>
              <div style={{ display: 'flex', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
                <button className="btn" onClick={() => copy(n.address)}>{copied === n.address ? t.copied : t.copy}</button>
                {txLinks[n.network] && <a className="btn btn-secondary" href={txLinks[n.network]} target="_blank" rel="noreferrer">{t.explorer}</a>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
