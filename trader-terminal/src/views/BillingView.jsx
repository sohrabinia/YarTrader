import React, { useEffect, useState } from 'react';
import { apiService } from '../services/api.js';

export default function BillingView({ lang='en' }) {
  const [sub,setSub]=useState(null),[invoices,setInvoices]=useState([]),[error,setError]=useState(''),[loading,setLoading]=useState(true);
  const t={fa:{title:'صورتحساب و اشتراک',sub:'وضعیت واقعی اشتراک و فاکتورهای ثبت‌شده',empty:'هنوز فاکتوری ثبت نشده است.',tier:'پلن',status:'وضعیت',renew:'تمدید',invoices:'فاکتورها'},ar:{title:'الفوترة والاشتراك',sub:'حالة الاشتراك والفواتير الفعلية',empty:'لا توجد فواتير بعد.',tier:'الخطة',status:'الحالة',renew:'التجديد',invoices:'الفواتير'},tr:{title:'Faturalama ve Abonelik',sub:'Gerçek abonelik ve fatura durumu',empty:'Henüz fatura yok.',tier:'Plan',status:'Durum',renew:'Yenileme',invoices:'Faturalar'},en:{title:'Billing & Subscription',sub:'Authoritative subscription and invoice state',empty:'No invoices recorded yet.',tier:'Plan',status:'Status',renew:'Renewal',invoices:'Invoices'}}[lang]||null;
  useEffect(()=>Promise.all([apiService.get('/api/user/billing/subscription'),apiService.get('/api/user/billing/invoices')]).then(([s,i])=>{setSub(s);setInvoices(i?.invoices||[])}).catch(e=>setError(e.message||'Unable to load billing.')).finally(()=>setLoading(false)),[]);
  if(loading)return <div className="card"><h2>{t.title}</h2><p>Loading…</p></div>;
  if(error)return <div className="card"><h2>{t.title}</h2><div className="status-warn">{error}</div></div>;
  return <div className="card" style={{maxWidth:980,margin:'0 auto'}}>
    <h2 style={{marginTop:0}}>{t.title}</h2><p style={{color:'var(--text-muted)'}}>{t.sub}</p>
    <div className="status-board" style={{marginTop:20}}>
      <div className="card"><small>{t.tier}</small><h3>{sub?.tier_id||'FREE'}</h3></div>
      <div className="card"><small>{t.status}</small><h3>{sub?.status||'INACTIVE'}</h3></div>
      <div className="card"><small>{t.renew}</small><h3>{sub?.renewal_date?new Date(Number(sub.renewal_date)*1000).toLocaleDateString(): '—'}</h3></div>
    </div>
    <h3>{t.invoices}</h3>
    {invoices.length===0?<p style={{color:'var(--text-muted)'}}>{t.empty}</p>:<DataTableShim rows={invoices}/>}
  </div>;
}
function DataTableShim({rows}){return <div style={{overflowX:'auto'}}><table style={{width:'100%',borderCollapse:'collapse'}}><thead><tr>{['Invoice','Tier','Amount','Status','Date'].map(h=><th key={h} style={{textAlign:'left',padding:10,borderBottom:'1px solid var(--border-dark)'}}>{h}</th>)}</tr></thead><tbody>{rows.map(r=><tr key={r.invoice_id}><td style={{padding:10}}>{r.invoice_id}</td><td>{r.tier_id}</td><td>{(Number(r.amount_cents||0)/100).toFixed(2)} {r.currency||'USD'}</td><td>{r.status}</td><td>{r.timestamp?new Date(r.timestamp).toLocaleDateString():'—'}</td></tr>)}</tbody></table></div>}
