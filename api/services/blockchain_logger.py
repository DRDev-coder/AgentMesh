import os
from web3 import Web3

# Free RPC fallback endpoints (no signup required)
FALLBACK_RPCS = [
    os.getenv("ALCHEMY_URL", ""),  # User's primary choice
    "https://rpc.ankr.com/polygon_mumbai",  # Ankr public
    "https://polygon-mumbai-bor-rpc.publicnode.com",  # PublicNode
    "https://rpc-mumbai.maticvigil.com",  # MaticVigil
]


class BlockchainLogger:
    def __init__(self):
        self.contract_address = os.getenv("CONTRACT_ADDRESS", "")
        self.wallet = os.getenv("WALLET_ADDRESS", "")
        self.private_key = os.getenv("PRIVATE_KEY", "")
        self.w3 = None
        self.contract = None

        # Try each RPC until one connects
        for rpc_url in FALLBACK_RPCS:
            if not rpc_url:
                continue
            try:
                w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
                if w3.is_connected():
                    self.w3 = w3
                    print(f"[Blockchain] Connected via: {rpc_url}")
                    break
            except Exception:
                continue

        if self.w3 and self.contract_address and self.contract_address != "0x0000000000000000000000000000000000000000":
            try:
                self.abi = [
                    {
                        "inputs": [
                            {"name": "_sessionId", "type": "bytes32"},
                            {"name": "_queryHash", "type": "bytes32"},
                            {"name": "_answerHash", "type": "bytes32"},
                            {"name": "_sageVote", "type": "bytes32"},
                            {"name": "_guardianVote", "type": "bytes32"},
                            {"name": "_empathVote", "type": "bytes32"},
                            {"name": "_oracleVote", "type": "bytes32"},
                            {"name": "_consensusReached", "type": "bool"},
                            {"name": "_status", "type": "string"}
                        ],
                        "name": "logConsensus",
                        "outputs": [],
                        "stateMutability": "nonpayable",
                        "type": "function"
                    }
                ]
                self.contract = self.w3.eth.contract(
                    address=Web3.to_checksum_address(self.contract_address),
                    abi=self.abi
                )
            except Exception as e:
                print(f"[Blockchain] Contract init failed: {e}")
                self.contract = None

    def log_consensus(self, session_id, query, answer, votes, consensus_reached, status):
        if not self.w3:
            return "BLOCKCHAIN_RPC_UNAVAILABLE"
        if not self.contract:
            return "BLOCKCHAIN_CONTRACT_NOT_CONFIGURED"
        if not self.wallet or not self.private_key:
            return "BLOCKCHAIN_WALLET_NOT_CONFIGURED"

        try:
            tx = self.contract.functions.logConsensus(
                self.w3.keccak(text=session_id),
                self.w3.keccak(text=query),
                self.w3.keccak(text=answer),
                self.w3.keccak(text=str(votes.get("sage", {}))),
                self.w3.keccak(text=str(votes.get("guardian", {}))),
                self.w3.keccak(text=str(votes.get("empath", {}))),
                self.w3.keccak(text=str(votes.get("oracle", {}))),
                consensus_reached,
                status
            ).build_transaction({
                'from': self.wallet,
                'nonce': self.w3.eth.get_transaction_count(self.wallet),
                'gas': 200000,
                'gasPrice': self.w3.to_wei('10', 'gwei')
            })

            signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            return tx_hash.hex()
        except Exception as e:
            return f"BLOCKCHAIN_ERROR: {str(e)}"
