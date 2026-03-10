import hashlib
import os
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

    def fetch_chat_history(self, target_username):
        """Fetches and decrypts the ENTIRE conversation history with target user."""
        if not self.is_authenticated: return []
        
        raw_msgs = self.server.db.get_messages_between(self.username, target_username)
        # Sort by ID or created_at (id is sequential UUID v4 or we can sort by timestamp if available)
        # Supposing 'created_at' is in the dictionary if we used select=*
        raw_msgs.sort(key=lambda x: x.get('created_at', ''))
        
        target_data = self.server.get_client_data(target_username)
        blockchain_root = self.server.get_blockchain_root()
        other_pub_bytes = target_data["public_key_bytes"]
        
        decrypted_history = []
        for msg in raw_msgs:
            sender = msg.get('sender_username')
            try:
                plaintext = self.crypto_engine.decrypt(
                    msg['ciphertext_b64'], msg['nonce_b64'], msg['timestamp_b64'], 
                    other_pub_bytes, blockchain_root
                )
                decrypted_history.append({
                    "id": msg.get("id"),
                    "sender": sender,
                    "text": plaintext,
                    "created_at": msg.get('created_at', '')
                })
            except Exception:
                pass # skip messages that can't be decrypted
                
        return decrypted_history

    def delete_messages_with(self, target_username):
        """Permanently deletes conversation history with target user."""
        if not self.is_authenticated: return False
        return self.server.db.delete_messages_between(self.username, target_username)

    def delete_burn_messages_with(self, target_username):
        """Permanently deletes ONLY [BURN] messages between self and target user."""
        if not self.is_authenticated: return False
        
        messages = self.server.db.get_messages_between(self.username, target_username)
        target_data = self.server.get_client_data(target_username)
        blockchain_root_bytes = self.server.get_blockchain_root()
        
        burn_msg_ids = []
        for msg in messages:
            try:
                # Provide the other party's public key to derive the same shared secret
                other_pub_bytes = target_data["public_key_bytes"]
                plaintext = self.crypto_engine.decrypt(
                    msg['ciphertext_b64'], msg['nonce_b64'], msg['timestamp_b64'], 
                    other_pub_bytes, blockchain_root_bytes
                )
                if plaintext.startswith("[BURN]"):
                    burn_msg_ids.append(msg['id'])
            except Exception:
                pass # Skip messages we can't decrypt (e.g. key rotation/tampering)
                
        if burn_msg_ids:
            return self.server.db.delete_messages_by_ids(burn_msg_ids)
        return True

    # --- 📂 FILE TRANSFER ---
    def upload_secure_file(self, local_path, recipient_username):
        """Encrypts and uploads a file to the secure_vault bucket for a recipient."""
        if not self.is_authenticated: return False
        
        if not os.path.exists(local_path):
            print(f"[{self.username}] ❌ File not found: {local_path}")
            return False

        recipient_data = self.server.get_client_data(recipient_username)
        blockchain_root_bytes = self.server.get_blockchain_root()
        
        with open(local_path, "rb") as f:
            file_bytes = f.read()
            
        encrypted_data = self.crypto_engine.encrypt_file(file_bytes, recipient_data["public_key_bytes"], blockchain_root_bytes)
        
        # Remote path: {recipient}/{sender}_{filename}.enc
        filename = os.path.basename(local_path)
        remote_path = f"{recipient_username}/{self.username}_{filename}.enc"
        
        return self.server.db.upload_file(encrypted_data, remote_path)

    def download_secure_file(self, remote_path, sender_username):
        """Downloads and decrypts a file from the secure_vault bucket."""
        if not self.is_authenticated: return None
        
        encrypted_data = self.server.db.download_file(remote_path)
        if not encrypted_data: return None
        
        sender_data = self.server.get_client_data(sender_username)
        blockchain_root_bytes = self.server.get_blockchain_root()
        
        return self.crypto_engine.decrypt_file(encrypted_data, sender_data["public_key_bytes"], blockchain_root_bytes)

    def list_my_files(self):
        """Lists files sent to me (received files) in the secure_vault bucket."""
        if not self.is_authenticated: return []
        return self.server.db.list_vault_files(prefix=f"{self.username}/")

    def list_sent_files(self):
        """Lists files I have sent to others in the secure_vault bucket."""
        if not self.is_authenticated: return []
        return self.server.db.list_sent_files(self.username)

    def get_verified_contacts(self):
        """Returns list of verified contact usernames from Supabase."""
        if not self.is_authenticated: return []
        return self.server.db.get_verified_contacts(self.username)

    def get_pending_requests(self):
        """Returns list of pending connection request usernames."""
        if not self.is_authenticated: return []
        return self.server.db.get_pending_requests(self.username)
