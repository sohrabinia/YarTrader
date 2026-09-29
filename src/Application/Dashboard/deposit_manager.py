import json, os, secrets, threading
from datetime import datetime, timezone
from typing import Any, Dict, List

class DepositManager:
    def __init__(self, filepath="runtime_logs/usdt_deposits.json"):
        self.filepath=filepath; self.lock=threading.RLock()
        os.makedirs(os.path.dirname(filepath),exist_ok=True)
        if not os.path.exists(filepath): self._save({"deposits":[]})

    def _load(self):
        try:
            with open(self.filepath,"r",encoding="utf-8") as f:return json.load(f)
        except Exception:return {"deposits":[]}
    def _save(self,d):
        tmp=self.filepath+".tmp"
        with open(tmp,"w",encoding="utf-8") as f:json.dump(d,f,indent=2,ensure_ascii=False)
        os.replace(tmp,self.filepath)
    def create(self,email,network,tx_hash,amount_usdt):
        network=network.upper().strip(); tx_hash=tx_hash.strip(); amount=float(amount_usdt)
        if network not in {"TON","TRC20","ERC20","BEP20","SOLANA"}: raise ValueError("Unsupported network.")
        if not tx_hash or len(tx_hash)>256 or amount<=0: raise ValueError("Invalid deposit reference or amount.")
        with self.lock:
            d=self._load()
            if any(x.get("network")==network and x.get("tx_hash")==tx_hash for x in d["deposits"]):
                raise ValueError("This transaction reference has already been submitted.")
            rec={"deposit_id":"dep-"+secrets.token_hex(10),"email":email.lower(),"asset":"USDT","network":network,
                 "tx_hash":tx_hash,"amount_usdt":round(amount,6),"status":"PENDING",
                 "created_at":datetime.now(timezone.utc).isoformat(),"verified_at":None,"verified_by":None}
            d["deposits"].append(rec); self._save(d); return rec
    def list_user(self,email): return [x for x in self._load()["deposits"] if x.get("email")==email.lower()]
    def list_all(self,status=None): return [x for x in self._load()["deposits"] if not status or x.get("status")==status]
    def set_status(self,deposit_id,status,admin_email):
        status=status.upper()
        if status not in {"VERIFIED","REJECTED"}: raise ValueError("Invalid deposit status.")
        with self.lock:
            d=self._load()
            for x in d["deposits"]:
                if x.get("deposit_id")==deposit_id:
                    if x.get("status")!="PENDING": raise ValueError("Deposit is already finalized.")
                    x["status"]=status;x["verified_at"]=datetime.now(timezone.utc).isoformat();x["verified_by"]=admin_email
                    self._save(d);return x
        raise ValueError("Deposit not found.")
