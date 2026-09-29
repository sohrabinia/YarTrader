import json
from pathlib import Path
from src.Application.Dashboard.ledger_manager import LedgerManager
from src.Application.Dashboard.receive_wallet_manager import ReceiveWalletManager
from src.Application.Dashboard.deposit_manager import DepositManager

def test_receive_wallet_and_deposit_flow(tmp_path):
    wallet=ReceiveWalletManager(str(tmp_path/"wallet.json"))
    out=wallet.set_network("TON","EQ_TEST_PUBLIC_ADDRESS","USDT TON")
    assert out["withdrawals_enabled"] is False
    assert out["networks"][0]["network"]=="TON"

    dep=DepositManager(str(tmp_path/"deposits.json"))
    rec=dep.create("user@example.com","TON","tx-test-1",12.5)
    assert rec["status"]=="PENDING"
    assert dep.list_user("user@example.com")[0]["amount_usdt"]==12.5
    verified=dep.set_status(rec["deposit_id"],"VERIFIED","admin@example.com")
    assert verified["status"]=="VERIFIED"

def test_ledger_statement(tmp_path):
    ledger=LedgerManager(str(tmp_path/"ledger.json"))
    ledger.post_transaction("k1",[
        {"account_id":"user@example.com","type":"credit","amount":1000},
        {"account_id":"SYSTEM","type":"debit","amount":1000},
    ],"USDT deposit")
    s=ledger.get_account_statement("user@example.com")
    assert s["balance"]==1000
    assert len(s["transactions"])==1
