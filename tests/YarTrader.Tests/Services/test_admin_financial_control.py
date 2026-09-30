from src.Application.Services.admin_api_router import admin_financial_overview
from src.Application.Dashboard.deposit_manager import DepositManager
from src.Application.Dashboard.receive_wallet_manager import ReceiveWalletManager

def test_financial_modules_import_and_receive_only(tmp_path):
    w=ReceiveWalletManager(str(tmp_path/'wallet.json'))
    cfg=w.set_network('TON','EQ_PUBLIC_TEST','USDT TON')
    assert cfg['withdrawals_enabled'] is False
    d=DepositManager(str(tmp_path/'deposits.json'))
    rec=d.create('finance-test@example.com','TON','tx-finance-test',5)
    assert rec['status']=='PENDING'
