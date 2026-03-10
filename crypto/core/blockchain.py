import time

class BlockchainLedger:
    def __init__(self):
        # Stores the history of Merkle Roots
        # Format: [{"timestamp": float, "root": bytes}]
        self.chain = []

    def update_root(self, new_root_bytes):
        """
        Appends a new Merkle Root to the ledger.
        This simulates 'mining a block'.
        """
        block = {
            "timestamp": time.time(),
            "root": new_root_bytes
        }
        self.chain.append(block)
        print(f"[Blockchain] 🔗 New Block Mined! Global Root Updated: {new_root_bytes.hex()[:15]}...")

    def get_latest_root(self):
        """
        Fetches the most recent Immutable Root.
        Clients use this to verify the Server is not lying.
        """
        if not self.chain:
            return b'' # Empty bytes if no users exist yet
        return self.chain[-1]["root"]