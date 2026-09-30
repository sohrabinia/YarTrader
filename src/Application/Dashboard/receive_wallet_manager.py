import json, os, threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from src.Infrastructure.exceptions import ValidationException

DEFAULT_PATH = "runtime_logs/wallet_receive.json"
SUPPORTED = {"TON", "TRC20", "ERC20", "BEP20", "SOLANA"}

class ReceiveWalletManager:
    """Public receive-only USDT configuration. No private keys, signing, or withdrawals."""
    def __init__(self, filepath: str = DEFAULT_PATH) -> None:
        self.filepath = filepath
        self.lock = threading.RLock()
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        self._ensure()

    def _ensure(self):
        with self.lock:
            if not os.path.exists(self.filepath):
                self._save({"asset":"USDT","mode":"RECEIVE_ONLY","networks":[],"updated_at":None})
            self._bootstrap_env()

    def _load(self):
        try:
            with open(self.filepath,"r",encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"asset":"USDT","mode":"RECEIVE_ONLY","networks":[],"updated_at":None}

    def _save(self, data):
        tmp=self.filepath+".tmp"
        with open(tmp,"w",encoding="utf-8") as f:
            json.dump(data,f,indent=2,ensure_ascii=False)
        os.replace(tmp,self.filepath)

    def _bootstrap_env(self):
        raw=os.getenv("YARTRADER_USDT_RECEIVE_CONFIG")
        if not raw: return
        try: cfg=json.loads(raw)
        except Exception: return
        networks=cfg.get("networks") if isinstance(cfg,dict) else None
        if not isinstance(networks,list): return
        clean=[]
        for item in networks:
            if not isinstance(item,dict): continue
            network=str(item.get("network","")).upper().strip()
            address=str(item.get("address","")).strip()
            if network in SUPPORTED and address and len(address)<=256:
                clean.append({"network":network,"asset":"USDT","address":address,"label":str(item.get("label") or network)})
        if clean:
            self._save({"asset":"USDT","mode":"RECEIVE_ONLY","networks":clean,"updated_at":datetime.now(timezone.utc).isoformat()})

    def public_config(self) -> Dict[str,Any]:
        with self.lock:
            data=self._load()
            return {"asset":"USDT","mode":"RECEIVE_ONLY","withdrawals_enabled":False,
                    "networks":data.get("networks",[]),"updated_at":data.get("updated_at")}

    def set_network(self, network:str, address:str, label:Optional[str]=None) -> Dict[str,Any]:
        network=network.upper().strip()
        address=address.strip()
        if network not in SUPPORTED: raise ValidationException("Unsupported receive network.")
        if not address or len(address)>256: raise ValidationException("Invalid receive address.")
        with self.lock:
            data=self._load()
            items=[x for x in data.get("networks",[]) if str(x.get("network","")).upper()!=network]
            items.append({"network":network,"asset":"USDT","address":address,"label":label or network})
            items.sort(key=lambda x:x["network"])
            data.update({"asset":"USDT","mode":"RECEIVE_ONLY","networks":items,"updated_at":datetime.now(timezone.utc).isoformat()})
            self._save(data)
            return self.public_config()

    def remove_network(self, network:str):
        network=network.upper().strip()
        with self.lock:
            data=self._load()
            data["networks"]=[x for x in data.get("networks",[]) if str(x.get("network","")).upper()!=network]
            data["updated_at"]=datetime.now(timezone.utc).isoformat()
            self._save(data)
            return self.public_config()

    def list_deposit_instructions(self) -> List[Dict[str,Any]]:
        return [{"network":x["network"],"asset":"USDT","address":x["address"],
                 "label":x.get("label",x["network"]),"receive_only":True} for x in self.public_config()["networks"]]
