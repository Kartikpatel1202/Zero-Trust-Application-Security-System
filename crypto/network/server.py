import time
from database.supabase_manager import SupabaseManager
from core.blockchain import BlockchainLedger
from core.merkle import MerkleTree

class ZTAServer:
    def __init__(self):
        print("[Server] Initializing Zero Trust Secure Cloud Server...")
        self.db = SupabaseManager() # <--- NOW USING SUPABASE
        self.blockchain = BlockchainLedger()
        self.merkle_tree = MerkleTree()
        
        self._load_existing_users()

    def _load_existing_users(self):
        """Rebuild the Merkle tree from Supabase. MUST clear & rebuild (not incremental)
        so Yash and Divya get identical root regardless of app startup order."""
        users = self.db.get_all_users()
        # DB returns order=username.asc - same order everywhere
        users_data = [(u['username'], bytes.fromhex(u['public_key_hex'])) for u in users]
        self.merkle_tree.rebuild_from_users(users_data)
        
        if self.merkle_tree.root:
            self.blockchain.update_root(self.merkle_tree.root)

    # --- 🛡️ ZERO TRUST ACCESS ---
    def authenticate(self, username, device_context):
        user_record = self.db.get_user(username)
        if not user_record:
            return False, "User not found in Cloud."

        trust_score = user_record[2]
        
        if trust_score < 50:
            return False, "Access Denied: Device trust score too low."
        if device_context.get("is_rooted", False):
            return False, "Access Denied: Compromised (Rooted) device detected."
        if device_context.get("location") == "Blacklisted_Region":
            return False, "Access Denied: Connection from unauthorized geo-location."

        print(f"[ZTA Gatekeeper] ✅ {username} authenticated.")
        return True, "Authenticated"

    # --- 🔑 IDENTITY & KEYS ---
    def register_client(self, username, public_key_bytes):
        public_key_hex = public_key_bytes.hex()
        leaf_hash = self.merkle_tree.add_leaf(username, public_key_bytes)
        
        self.db.register_user(username, public_key_hex, leaf_hash)
        self.blockchain.update_root(self.merkle_tree.root)
        return True, "Registration Complete."

    def get_client_data(self, requested_username):
        user_record = self.db.get_user(requested_username)
        if not user_record: return None
        return {
            "public_key_bytes": bytes.fromhex(user_record[0]),
            "proof": self.merkle_tree.get_proof(requested_username)
        }

    def get_blockchain_root(self):
        return self.blockchain.get_latest_root()

    # --- 🤝 THE HANDSHAKE LAYER ---
    def initiate_handshake(self, requester, receiver):
        """Starts the process. Client must verify Merkle Root next."""
        return self.db.request_connection(requester, receiver)

    def finalize_handshake(self, requester, receiver):
        """Called by the client AFTER they verify the math."""
        return self.db.verify_connection(requester, receiver)

    # --- ✉️ SECURE ROUTING ---
    def route_message(self, sender, recipient, packet):
        # The Server checks with Supabase: "Are they allowed to talk?"
        if not self.db.check_connection_status(sender, recipient):
            print(f"[Server Router] 🛑 BLOCKED: {sender} -> {recipient} (No verified connection)")
            return False
            
        self.db.store_message(
            sender=sender, recipient=recipient,
            ciphertext=packet["ciphertext_b64"], nonce=packet["nonce_b64"], timestamp=packet["timestamp_b64"]
        )
        print(f"[Server Router] 🔒 Encrypted packet routed.")
        return True

    def fetch_messages(self, username):
        return self.db.get_messages_for(username)