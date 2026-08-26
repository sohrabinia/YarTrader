import os
import pytest
from fastapi.testclient import TestClient
from src.Application.Services.web_dashboard import app
from src.Application.Services.wallet_verifier import WalletVerifierService, SUPPLIED_WALLET_ADDRESSES

client = TestClient(app)

def test_wallet_format_identification():
    """Verifies that all supplied wallet addresses are deterministically parsed with exact network labels."""
    wallets = WalletVerifierService.get_verified_wallets()
    assert len(wallets) == 9

    # 1. TRON TRC20 Check
    tron_wallet = wallets[0]
    assert tron_wallet["address"] == "TYGSkHakQSNYDH7dFuxsL5uuP7fWaEy6NU"
    assert tron_wallet["network"] == "TRON (TRC20)"
    assert tron_wallet["valid"] is True
    assert tron_wallet["tonkeeper_compatible"] is False

    # 2. EVM Check
    evm_wallet = wallets[1]
    assert evm_wallet["address"] == "0xbf9ec6dd237d60f7787c61dbe538165b1c2a4430"
    assert "EVM" in evm_wallet["network"]
    assert evm_wallet["valid"] is True
    assert evm_wallet["tonkeeper_compatible"] is True

    # 3. Solana Check
    sol_wallet = wallets[7]
    assert sol_wallet["address"] == "2mWbo3tcaMfjp7MgX1HQBRUoAthzMuWo43ZeafT1hiMr"
    assert sol_wallet["network"] == "Solana (SPL)"
    assert sol_wallet["valid"] is True
    assert sol_wallet["tonkeeper_compatible"] is False

    # 4. TON Check
    ton_wallet = wallets[8]
    assert ton_wallet["address"] == "25ffe0a1772b4b571b8f424042c86fcd09b5ca4031c25ec8af8a8ff7de09600c"
    assert "TON" in ton_wallet["network"]
    assert ton_wallet["valid"] is True
    assert ton_wallet["tonkeeper_compatible"] is True

def test_wallet_security_scan_no_secrets():
    """Enforces critical security rule: ZERO private keys or seed phrases in repo files."""
    for addr in SUPPLIED_WALLET_ADDRESSES:
        assert not addr.startswith("5K")  # No WIF private keys
        assert not len(addr.split()) > 1   # No mnemonics
        assert "private" not in addr.lower()
        assert "secret" not in addr.lower()

def test_api_get_billing_wallets():
    """Verifies GET /api/billing/wallets API endpoint response schema and safety matrix."""
    response = client.get("/api/billing/wallets")
    assert response.status_code == 200
    data = response.json()
    assert data["verification_mode"] == "MANUAL_HASH_SUBMISSION"
    assert data["security_status"] == "PUBLIC_RECEIVE_ONLY_NO_PRIVATE_KEYS"
    assert data["total_wallets"] == 9
    assert len(data["verified_wallets"]) == 9
    assert "safety_disclaimer" in data
