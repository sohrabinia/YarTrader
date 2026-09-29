import React, { useEffect, useState } from 'react';
import { apiService } from '../services/api.js';

export default function WalletView({ lang = 'en' }) {
  const [wallet, setWallet] = useState(null);
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
  useEffect(() => {
    apiService.get('/api/user/wallet/receive')
      .then(setWallet)
      .catch(e => setError(e.message || 'Unable to load wallet configuration.'))
      .finally(() => setLoading(false));
  }, []);
  const copy = async (address) => {
    try { await navigator.clipboard.writeText(address); } catch (_) {}
  };
  const text = {
    fa: { title:'کیف پول دریافت USDT', sub:'فقط دریافت — برداشت و ارسال از YarTrader فعال نیست.', empty:'هنوز آدرس دریافت برای شبکه‌ای پیکربندی نشده است.', copy:'کپی آدرس', copied:'آدرس کپی شد', network:'شبکه', warning:'قبل از واریز، شبکه را دقیقاً با شبکه انتخابی فرستنده تطبیق دهید.' },
    ar: { title:'محفظة استلام USDT', sub:'استلام فقط — السحب والإرسال من YarTrader غير متاحين.', empty:'لم يتم إعداد عنوان استلام لأي شبكة بعد.', copy:'نسخ العنوان', copied:'تم نسخ العنوان', network:'الشبكة', warning:'طابق الشبكة بدقة قبل الإيداع.' },
    tr: { title:'USDT Alma Cüzdanı', sub:'Yalnızca alma — YarTrader üzerinden çekim veya gönderim yoktur.', empty:'Henüz hiçbir ağ için alım adresi yapılandırılmadı.', copy:'Adresi kopyala', copied:'Adres kopyalandı', network:'Ağ', warning:'Yatırmadan önce gönderici ağını tam olarak eşleştirin.' },
    en: { title:'USDT Receive Wallet', sub:'Receive only — withdrawals and outbound transfers are disabled.', empty:'No receive address has been configured yet.', copy:'Copy address', copied:'Address copied', network:'Network', warning:'Match the sender network exactly before depositing.' }
  }[lang] || null;
  if (loading) return <div className="card"><h2>{text?.title || 'USDT Receive Wallet'}</h2><p>Loading…</p></div>;
  if (error) return <div className="card"><h2>{text?.title || 'USDT Receive Wallet'}</h2><div className="status-warn">{error}</div></div>;
  const networks = wallet?.networks || [];
  return <div className="card" dir={rtl ? 'rtl' : 'ltr'} style={{maxWidth:'980px',margin:'0 auto'}}>
    <div style={{display:'flex',justifyContent:'space-between',gap:16,alignItems:'flex-start',flexWrap:'wrap'}}>
      <div><h2 style={{marginTop:0}}>{text?.title}</h2><p style={{color:'var(--text-muted)'}}>{text?.sub}</p></div>
      <span className="status-passed">RECEIVE ONLY</span>
    </div>
    <div style={{padding:'12px 14px',border:'1px solid var(--border-dark)',borderRadius:8,margin:'18px 0',color:'var(--text-muted)'}}>⚠️ {text?.warning}</div>
    {networks.length === 0 ? <div style={{padding:'35px 10px',textAlign:'center',color:'var(--text-muted)'}}>{text?.empty}</div> :
      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(300px,1fr))',gap:16}}>
        {networks.map((n) => <div key={n.network} style={{border:'1px solid var(--border-dark)',borderRadius:10,padding:18}}>
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:12}}>
            <strong>{n.label || n.network}</strong><span className="status-passed">{n.network}</span>
          </div>
          <div style={{fontSize:12,color:'var(--text-muted)',marginBottom:6}}>{text?.network}: {n.network} · USDT</div>
          <code style={{display:'block',wordBreak:'break-all',padding:12,background:'rgba(15,23,42,.45)',borderRadius:6}}>{n.address}</code>
          <div style={{display:'flex',gap:8,marginTop:12}}>
            <button className="btn" onClick={() => copy(n.address)}>{text?.copy}</button>
            {txLinks[n.network] && <a className="btn btn-secondary" href={txLinks[n.network]} target="_blank" rel="noreferrer">Explorer</a>}
          </div>
        </div>)}
      </div>}
  </div>;
}
