import re
from typing import Dict, Any, List, Optional

SUPPLIED_WALLET_ADDRESSES = [
    "TYGSkHakQSNYDH7dFuxsL5uuP7fWaEy6NU",
    "0xbf9ec6dd237d60f7787c61dbe538165b1c2a4430",
    "0x735b8d95494708a2c0fa0254424c55f90dc48182",
    "0x8ff8da67258580bb6749bcb703397a3485bf1ce2",
    "0x5182aeea8d941f45e6427e6d740cbf380470996c",
    "0xed59ae4825cbc0a821ee883175e342f6fff70b17",
    "0x8d76c527e210ed7dcf1df8e92dcf1a98c7f01a90",
    "2mWbo3tcaMfjp7MgX1HQBRUoAthzMuWo43ZeafT1hiMr",
    "25ffe0a1772b4b571b8f424042c86fcd09b5ca4031c25ec8af8a8ff7de09600c"
]

BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

def is_valid_base58(s: str) -> bool:
    return all(c in BASE58_ALPHABET for c in s)

class WalletVerifierService:
    """
    Forensic Wallet Identification and Security Verification Service.
    Parses public cryptocurrency receive addresses, identifies blockchain format,
    validates structure, maps to explorer URLs, and enforces payment safety.
    """

    @staticmethod
    def identify_address(address: str) -> Dict[str, Any]:
        address = address.strip()

        # 1. TRON (TRC20) Check
        if address.startswith("T") and len(address) == 34 and is_valid_base58(address):
            return {
                "address": address,
                "network": "TRON (TRC20)",
                "family": "TRON",
                "asset": "USDT / TRX",
                "format": "Base58 (34 chars, T prefix)",
                "valid": True,
                "status": "VERIFIED",
                "tonkeeper_compatible": False,  # Tonkeeper primary is TON/EVM; TRON requires TRON wallet
                "explorer": f"https://tronscan.org/#/address/{address}",
                "warning": "Send ONLY TRC20 (TRON) USDT or TRX to this address. Sending via ERC20 or BSC will result in asset loss."
            }

        # 2. EVM (ERC20 / BEP20 / Polygon / Arbitrum) Check
        if address.startswith("0x") and len(address) == 42 and re.match(r"^0x[0-9a-fA-F]{40}$", address):
            return {
                "address": address,
                "network": "Ethereum / EVM (ERC20 / BEP20)",
                "family": "EVM",
                "asset": "USDT / USDC / ETH / BNB",
                "format": "Hexadecimal (42 chars, 0x prefix)",
                "valid": True,
                "status": "VERIFIED",
                "tonkeeper_compatible": True,  # Tonkeeper EVM multi-chain support
                "explorer": f"https://etherscan.io/address/{address}",
                "warning": "Send ONLY EVM compatible assets (ERC20 / BEP20) to this address. Verify gas network before sending."
            }

        # 3. Solana (SPL) Check
        if len(address) in (43, 44) and is_valid_base58(address) and not address.startswith("T") and not address.startswith("0x"):
            return {
                "address": address,
                "network": "Solana (SPL)",
                "family": "SOLANA",
                "asset": "USDT / USDC / SOL",
                "format": "Base58 (44 chars)",
                "valid": True,
                "status": "VERIFIED",
                "tonkeeper_compatible": False,  # Tonkeeper is TON ecosystem; Phantom/Solflare recommended for SPL
                "explorer": f"https://solscan.io/account/{address}",
                "warning": "Send ONLY Solana (SPL) network assets to this address."
            }

        # 4. TON Raw Public Key / Address Check
        if len(address) == 64 and re.match(r"^[0-9a-fA-F]{64}$", address):
            return {
                "address": address,
                "network": "TON (The Open Network - Raw Hex)",
                "family": "TON",
                "asset": "TON / Jettons",
                "format": "Hexadecimal (64 chars, Raw Key)",
                "valid": True,
                "status": "VERIFIED",
                "tonkeeper_compatible": True,  # Tonkeeper native TON chain
                "explorer": f"https://tonscan.org/address/{address}",
                "warning": "This is a raw TON account hash. Use Tonkeeper or TON native wallet for TON transfer."
            }

        return {
            "address": address,
            "network": "UNKNOWN",
            "family": "UNRECOGNIZED",
            "asset": "UNSPECIFIED",
            "format": "INVALID_OR_UNKNOWN",
            "valid": False,
            "status": "UNVERIFIED",
            "tonkeeper_compatible": False,
            "explorer": "#",
            "warning": "Unrecognized address format. DO NOT send funds."
        }

    @classmethod
    def get_verified_wallets(cls) -> List[Dict[str, Any]]:
        results = []
        for idx, addr in enumerate(SUPPLIED_WALLET_ADDRESSES, 1):
            info = cls.identify_address(addr)
            info["id"] = f"wallet-{idx}"
            results.append(info)
        return results

    @classmethod
    def get_pricing_wallet_matrix(cls) -> Dict[str, Any]:
        wallets = cls.get_verified_wallets()
        return {
            "verification_mode": "MANUAL_HASH_SUBMISSION",
            "security_status": "PUBLIC_RECEIVE_ONLY_NO_PRIVATE_KEYS",
            "total_wallets": len(wallets),
            "verified_wallets": [w for w in wallets if w["valid"]],
            "networks_supported": ["TRON (TRC20)", "Ethereum / EVM (ERC20 / BEP20)", "Solana (SPL)", "TON"],
            "safety_disclaimer": "Verify network compatibility prior to transferring assets. Transactions on wrong networks cannot be recovered automatically."
        }
