import React,{useEffect,useState} from 'react';
import {apiService} from '../services/api.js';
export default function AdminWalletView(){
 const [w,setW]=useState({networks:[]}),[deps,setDeps]=useState([]),[network,setNetwork]=useState('TON'),[address,setAddress]=useState(''),[msg,setMsg]=useState('');
 const load=()=>Promise.all([apiService.get('/api/admin/wallet/receive'),apiService.get('/api/admin/wallet/deposits?status=PENDING')]).then(([a,d])=>{setW(a);setDeps(d.deposits||[])}).catch(e=>setMsg(e.message||'Load failed'));
 useEffect(load,[]);
 const save=async()=>{try{await apiService.post('/api/admin/wallet/receive',{network,address,label:'USDT '+network});setAddress('');setMsg('Receive address saved.');load()}catch(e){setMsg(e.message)}};
 const finalize=async(id,action)=>{try{await apiService.post('/api/admin/wallet/deposits/'+id+'/'+action);load()}catch(e){setMsg(e.message)}};
 return <div className="card" style={{maxWidth:1100,margin:'0 auto'}}><h2 style={{marginTop:0}}>USDT Receive & Deposit Control</h2>
 <p style={{color:'var(--text-muted)'}}>Receive-only. No private key, signing, withdrawal, or outbound transfer capability is exposed.</p>
 <div style={{display:'grid',gridTemplateColumns:'160px 1fr auto',gap:10,margin:'20px 0'}}><select className="form-input" value={network} onChange={e=>setNetwork(e.target.value)}>{['TON','TRC20','ERC20','BEP20','SOLANA'].map(n=><option key={n}>{n}</option>)}</select><input className="form-input" placeholder="Public receive address" value={address} onChange={e=>setAddress(e.target.value)}/><button className="btn" onClick={save}>Save address</button></div>
 {msg&&<div style={{color:'var(--text-muted)',marginBottom:15}}>{msg}</div>}
 <h3>Configured receive addresses</h3>{w.networks.map(n=><div key={n.network} style={{padding:12,borderBottom:'1px solid var(--border-dark)',wordBreak:'break-all'}}><strong>{n.network}</strong> · {n.address}</div>)}
 <h3 style={{marginTop:28}}>Pending deposits</h3>{deps.length===0?<p style={{color:'var(--text-muted'}}>No pending deposits.</p>:deps.map(d=><div key={d.deposit_id} style={{padding:14,border:'1px solid var(--border-dark)',borderRadius:8,marginBottom:10}}><strong>{d.amount_usdt} USDT</strong> · {d.network} · {d.email}<div style={{fontSize:12,wordBreak:'break-all',margin:'8px 0'}}>{d.tx_hash}</div><button className="btn" onClick={()=>finalize(d.deposit_id,'verify')}>Verify</button> <button className="btn btn-secondary" onClick={()=>finalize(d.deposit_id,'reject')}>Reject</button></div>)}</div>
}