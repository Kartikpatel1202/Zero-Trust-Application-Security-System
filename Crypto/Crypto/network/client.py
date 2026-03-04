import hashlib
from core.crypto_utils import CryptoEngine

class SecureClient:
    def __init__(self, username, server, private_key_bytes=None):
        """
        private_key_bytes: If provided, loads existing identity. Required for login
        to decrypt messages. If None, generates new keys (use for registration only).
        """
        self.username = username
        self.server = server
        self.crypto_engine = CryptoEngine(private_key_bytes=private_key_bytes)
        self.is_authenticated = False

    def register(self):
        pub_bytes = self.crypto_engine.get_public_bytes()
        success, msg = self.server.register_client(self.username, pub_bytes)
        print(f"[{self.username}] Registration: {msg}")

    def login(self, device_context):
        print(f"\n[{self.username}] Requesting Zero Trust network access...")
        success, msg = self.server.authenticate(self.username, device_context)
        if success:
            self.is_authenticated = True
        else:
            print(f"[{self.username}] 🚨 {msg}")
        return self.is_authenticated

    # --- 🤝 NEW: THE HANDSHAKE PROTOCOL ---
    def request_connection(self, target_username):
        """Step 1: Ask to connect."""
        if not self.is_authenticated: return
        print(f"[{self.username}] Sending secure connection request to {target_username}...")
        self.server.initiate_handshake(self.username, target_username)

    def verify_and_accept_connection(self, requester_username):
        """Step 2: Verify their math/identity, then accept."""
        if not self.is_authenticated: return
        print(f"[{self.username}] Received request from {requester_username}. Verifying identity...")
        
        requester_data = self.server.get_client_data(requester_username)
        blockchain_root = self.server.get_blockchain_root()
        
        # Verify Identity via Blockchain BEFORE accepting
        if self._verify_merkle_proof(requester_username, requester_data["public_key_bytes"], requester_data["proof"], blockchain_root):
            self.server.finalize_handshake(requester_username, self.username)
            print(f"[{self.username}] ✅ Identity verified. Connection established with {requester_username}.")
        else:
            print(f"[{self.username}] 🚨 Identity verification failed. Connection BLOCKED.")

    def _verify_merkle_proof(self, target_username, public_key_bytes, proof, blockchain_root_bytes):
        calculated_hash = hashlib.blake2b(public_key_bytes, digest_size=32).hexdigest()
        if calculated_hash != proof["leaf_hash"]: return False
        if proof["global_root_hex"] != blockchain_root_bytes.hex(): return False
        return True

    # --- ✉️ MESSAGING ---
    def send_message(self, recipient_username, plaintext_message):
        if not self.is_authenticated: return

        recipient_data = self.server.get_client_data(recipient_username)
        blockchain_root_bytes = self.server.get_blockchain_root()
        
        # Double check identity before encrypting
        if not self._verify_merkle_proof(recipient_username, recipient_data["public_key_bytes"], recipient_data["proof"], blockchain_root_bytes):
            print(f"[{self.username}] 🛑 Aborting send. Security failure.")
            return

        packet = self.crypto_engine.encrypt(plaintext_message, recipient_data["public_key_bytes"], blockchain_root_bytes)
        
        # Server will route it ONLY if the handshake was completed
        self.server.route_message(self.username, recipient_username, packet)

    def check_inbox(self):
        if not self.is_authenticated: return
        messages = self.server.fetch_messages(self.username)
        if not messages:
            print(f"[{self.username}] Inbox is empty.")
            return

        print(f"\n[{self.username}] 📥 You have {len(messages)} new message(s):")
        for msg in messages:
            msg_id, sender, _, ciphertext_b64, nonce_b64, timestamp_b64, _ = msg
            sender_data = self.server.get_client_data(sender)
            blockchain_root_bytes = self.server.get_blockchain_root()
            
            try:
                plaintext = self.crypto_engine.decrypt(
                    ciphertext_b64, nonce_b64, timestamp_b64, 
                    sender_data["public_key_bytes"], blockchain_root_bytes
                )
                print(f"  💬 From {sender}: {plaintext}")
            except Exception as e:
                print(f"  -> 🚨 Could not decrypt message from {sender}: {e}")