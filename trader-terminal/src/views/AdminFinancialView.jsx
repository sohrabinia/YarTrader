import React,{useEffect,useState} from 'react';
import {apiService} from '../services/api.js';
export default function AdminFinancialView(){
 const [data,setData]=useState(null),[msg,setMsg]=useState('');
 const load=()=>apiService.get('/api/admin/financial/overview').then(setData).catch(e=>setMsg(e.message||'Unable to load financial data.'));
 useEffect(load,[]);
 if(msg)return <div className="card"><h2>Financial Control</h2><div className="status-warn">{msg}</div></div>;
 if(!data)return <div className="card"><h2>Financial Control</h2><p>Loading…</p></div>;
 const money=(v,c='USD')=>{const n=Number(v||0);const value=c==='USDT'?n/1000000:n/100;return value.toFixed(c==='USDT'?6:2)+' '+c;};
 return <div className="space-y-6" style={{maxWidth:1200,margin:'0 auto'}}>
  <div className="card"><h2 style={{marginTop:0}}>💳 Financial Control Center</h2><p style={{color:'var(--text-muted)'}}>Authoritative financial state. No synthetic balances and no withdrawal capability.</p></div>
  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
   <div className="card"><small>Ledger Accounts</small><h3>{data.ledger.account_count}</h3></div><div className="card"><small>Ledger Transactions</small><h3>{data.ledger.transaction_count}</h3></div><div className="card"><small>Pending Deposits</small><h3>{data.deposits.pending}</h3></div><div className="card"><small>Invoices</small><h3>{data.billing.invoice_count}</h3></div>
  </div>
  <div className="card"><h3>USDT Deposits</h3>{data.deposits.items.length===0?<p style={{color:'var(--text-muted)'}}>No deposits recorded.</p>:<div style={{overflowX:'auto'}}><table style={{width:'100%'}}><thead><tr><th>Account</th><th>Network</th><th>Amount</th><th>Status</th><th>TX</th><th>Action</th></tr></thead><tbody>{data.deposits.items.map(d=><tr key={d.deposit_id}><td>{d.email}</td><td>{d.network}</td><td>{d.amount_usdt} USDT</td><td>{d.status}</td><td style={{maxWidth:260,wordBreak:'break-all'}}>{d.tx_hash}</td><td>{d.status==='PENDING'&&<><button className="btn" onClick={()=>apiService.post('/api/admin/wallet/deposits/'+d.deposit_id+'/verify').then(load)}>Verify</button> <button className="btn btn-secondary" onClick={()=>apiService.post('/api/admin/wallet/deposits/'+d.deposit_id+'/reject').then(load)}>Reject</button></>}</td></tr>)}</tbody></table></div>}</div>
  <div className="card"><h3>Ledger Accounts</h3>{data.ledger.accounts.length===0?<p style={{color:'var(--text-muted)'}}>No ledger accounts recorded.</p>:<div style={{overflowX:'auto'}}><table style={{width:'100%'}}><thead><tr><th>Account</th><th>Balance</th><th>Currency</th></tr></thead><tbody>{data.ledger.accounts.map(a=><tr key={a.account_id}><td>{a.account_id}</td><td>{money(a.balance,a.currency)}</td><td>{a.currency}</td></tr>)}</tbody></table></div>}</div>
  <div className="card"><h3>Invoices</h3>{data.billing.invoices.length===0?<p style={{color:'var(--text-muted)'}}>No invoices recorded.</p>:data.billing.invoices.map(i=><div key={i.invoice_id} style={{padding:10,borderBottom:'1px solid var(--border-dark)'}}>{i.invoice_id} · {i.email||'—'} · {money(i.amount_cents,i.currency)} · {i.status}</div>)}</div>
  <div className="card"><strong>Withdrawal status: DISABLED</strong><p style={{color:'var(--text-muted)',marginBottom:0}}>This control plane can receive and verify deposits only. It contains no private-key signing or outbound transfer operation.</p></div>
 </div>;
}