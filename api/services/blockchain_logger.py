from __future__ import annotations

import json
import os
import threading
from typing import Any

from shared.schemas import AuditOutcome, AuditStatus


_DECISION_ABI = [
    {
        "inputs": [
            {"name": "recordId", "type": "bytes32"},
            {"name": "decisionHash", "type": "bytes32"},
            {"name": "status", "type": "string"},
        ],
        "name": "logDecision",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]


def _enabled(value: str | None) -> bool:
    return str(value or "").lower() in {"1", "true", "yes", "on"}


class BlockchainLogger:
    """Optional secondary audit sink; SQLite remains authoritative."""

    def __init__(self):
        self.enabled = _enabled(os.getenv("BLOCKCHAIN_ENABLED", "false"))
        self.rpc_url = os.getenv("BLOCKCHAIN_RPC_URL", os.getenv("ALCHEMY_URL", ""))
        self.contract_address = os.getenv(
            "BLOCKCHAIN_CONTRACT_ADDRESS", os.getenv("CONTRACT_ADDRESS", "")
        )
        self.wallet = os.getenv(
            "BLOCKCHAIN_WALLET_ADDRESS", os.getenv("WALLET_ADDRESS", "")
        )
        self.private_key = os.getenv(
            "BLOCKCHAIN_PRIVATE_KEY", os.getenv("PRIVATE_KEY", "")
        )
        self.network = os.getenv("BLOCKCHAIN_NETWORK", "local")
        self.explorer_url = os.getenv("BLOCKCHAIN_EXPLORER_URL", "").rstrip("/") or None
        self.receipt_timeout = int(os.getenv("BLOCKCHAIN_RECEIPT_TIMEOUT", "30"))
        self._nonce_lock = threading.Lock()

    @property
    def configured(self) -> bool:
        return bool(
            self.enabled
            and self.rpc_url
            and self.contract_address
            and self.wallet
            and self.private_key
        )

    def log_decision(
        self,
        *,
        session_id: str,
        status: str,
        trace: dict[str, Any],
    ) -> AuditOutcome:
        if not self.enabled:
            return AuditOutcome(
                status=AuditStatus.DISABLED,
                network=self.network,
                explorer_url=self.explorer_url,
            )
        if not self.configured:
            return AuditOutcome(
                status=AuditStatus.FAILED,
                error="Blockchain audit is enabled but configuration is incomplete.",
                network=self.network,
                explorer_url=self.explorer_url,
            )

        try:
            from web3 import Web3

            web3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={"timeout": 8}))
            if not web3.is_connected():
                raise ConnectionError("RPC unavailable")
            contract = web3.eth.contract(
                address=Web3.to_checksum_address(self.contract_address),
                abi=_DECISION_ABI,
            )
            canonical = json.dumps(
                trace, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            )
            decision_hash = web3.keccak(text=canonical)
            record_id = web3.keccak(
                text=f"{session_id}:{decision_hash.hex()}"
            )
            with self._nonce_lock:
                transaction = contract.functions.logDecision(
                    record_id,
                    decision_hash,
                    status,
                ).build_transaction(
                    {
                        "from": Web3.to_checksum_address(self.wallet),
                        "nonce": web3.eth.get_transaction_count(self.wallet, "pending"),
                        "chainId": web3.eth.chain_id,
                        "gasPrice": web3.eth.gas_price,
                    }
                )
                signed = web3.eth.account.sign_transaction(transaction, self.private_key)
                raw_transaction = getattr(signed, "raw_transaction", None) or getattr(
                    signed, "rawTransaction"
                )
                transaction_hash = web3.eth.send_raw_transaction(raw_transaction)

            hash_text = transaction_hash.hex()
            try:
                receipt = web3.eth.wait_for_transaction_receipt(
                    transaction_hash, timeout=self.receipt_timeout
                )
            except Exception:
                return AuditOutcome(
                    status=AuditStatus.SUBMITTED,
                    transaction_hash=hash_text,
                    error="Transaction submitted but confirmation was not observed in time.",
                    network=self.network,
                    explorer_url=self.explorer_url,
                )
            if receipt.status != 1:
                return AuditOutcome(
                    status=AuditStatus.FAILED,
                    transaction_hash=hash_text,
                    error="Transaction receipt reported failure.",
                    network=self.network,
                    explorer_url=self.explorer_url,
                )
            return AuditOutcome(
                status=AuditStatus.CONFIRMED,
                transaction_hash=hash_text,
                network=self.network,
                explorer_url=self.explorer_url,
            )
        except Exception as exc:
            return AuditOutcome(
                status=AuditStatus.FAILED,
                error=f"Blockchain audit failed: {type(exc).__name__}",
                network=self.network,
                explorer_url=self.explorer_url,
            )
