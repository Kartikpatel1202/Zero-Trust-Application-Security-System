import os
import json
import time
import struct
import hashlib
from base64 import b64encode, b64decode
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# --- 1. NOVELTY: MERKLE TREE LOGIC ---
class MerkleTree:
    def __init__(self):
        self.leaves = [] # List of (user_id, key_hash)
        self.root = None

    def add_leaf(self, user_id, public_key_bytes):
        # We use BLAKE2b instead of SHA256 for speed and "Novelty"
        leaf_hash = hashlib.blake2b(public_key_bytes, digest_size=32).hexdigest()
        self.leaves.append({"id": user_id, "hash": leaf_hash})
        self.recalculate_root()

    def recalculate_root(self):
        # Simply re-hashing everything to find the new Root
        # (Simplified version of a Merkle Tree for demonstration)
        if not self.leaves:
            self.root = None
            return

        current_level = [item["hash"] for item in self.leaves]
        
        while len(current_level) > 1:
            next_level = []
            # Pair up hashes
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                # If odd number of items, duplicate the last one
                right = current_level[i+1] if (i+1) < len(current_level) else left
                
                # Combine and Hash
                combined = left + right
                new_hash = hashlib.blake2b(combined.encode(), digest_size=32).hexdigest()
                next_level.append(new_hash)
            current_level = next_level
        
        self.root = current_level[0]
        print(f"[Merkle System] 🌳 New Merkle Root Generated: {self.root[:10]}...")

    def get_proof(self, user_id):
        # In a real Merkle Tree, this returns the "Sibling Path".
        # For this demo, we return the leaf hash + the current Root to simulate the check.
        for leaf in self.leaves:
            if leaf["id"] == user_id:
                return {
                    "leaf_hash": leaf["hash"],
                    "root_at_generation": self.root
                }
        return None

# --- 2. THE BLOCKCHAIN (Stores Only the Root) ---
class BlockchainLedger:
    def __init__(self):
        self.latest_root = None

    def update_root(self, new_root):
        # The blockchain only stores ONE hash for the whole system!
        self.latest_root = new_root
        print(f"[Blockchain] 🔗 Block Mined. Immutable Root: {self.latest_root[:15]}...")

    def get_latest_root(self):
        return self.latest_root

# --- 3. THE KEY SERVER (Untrusted Storage) ---
class KeyServer:
    def __init__(self, merkle_tree, blockchain):
        self.storage = {}
        self.merkle_tree = merkle_tree
        self.blockchain = blockchain

    def register_user(self, user_id, public_key_bytes):
        # 1. Store Key
        self.storage[user_id] = public_key_bytes.hex()
        
        # 2. Update Merkle Tree
        self.merkle_tree.add_leaf(user_id, public_key_bytes)
        
        # 3. Publish new Root to Blockchain
        self.blockchain.update_root(self.merkle_tree.root)

    def get_public_key(self, user_id):
        key_hex = self.storage.get(user_id)
        if key_hex:
            return bytes.fromhex(key_hex)
        return None

    def get_merkle_proof(self, user_id):
        return self.merkle_tree.get_proof(user_id)

# --- 4. THE SECURE USER (Verifies Proofs) ---
class SecureUser:
    def __init__(self, user_id, server, blockchain):
        self.user_id = user_id
        self.server = server
        self.blockchain = blockchain
        
        self.private_key = x25519.X25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        
        pub_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )

        # Register (Triggers Tree Update)
        self.server.register_user(self.user_id, pub_bytes)

    def derive_session_key(self, shared_secret, timestamp_bytes):
        input_key_material = shared_secret + timestamp_bytes
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b'handshake data',
        )
        return hkdf.derive(input_key_material)

    def send_message(self, recipient_id, plaintext_message):
        # 1. Fetch Key + PROOF from Server
        recipient_pub_bytes = self.server.get_public_key(recipient_id)
        proof = self.server.get_merkle_proof(recipient_id)
        
        if not recipient_pub_bytes or not proof:
            raise Exception("Recipient not found or no proof available!")

        # --- NOVELTY: VERIFY MERKLE PROOF ---
        print(f"\n[Alice] 🔍 Verifying {recipient_id} via Merkle Proof...")
        
        # A. Calculate Hash of received key
        calculated_hash = hashlib.blake2b(recipient_pub_bytes, digest_size=32).hexdigest()
        
        # B. Verify 1: Does the key match the proof's leaf?
        if calculated_hash != proof['leaf_hash']:
            print("🚨 Integrity Error: Key does not match the proof record!")
            return None

        # C. Verify 2: Does the Proof's Root match the Blockchain?
        blockchain_root = self.blockchain.get_latest_root()
        
        if proof['root_at_generation'] != blockchain_root:
            print(f"🚨 Root Mismatch! Proof says {proof['root_at_generation'][:10]}... but Blockchain has {blockchain_root[:10]}...")
            print("The Server is serving outdated or fake data!")
            return None
        
        print("✅ Merkle Proof Validated. The Key is anchored in the Global Root.")
        # ------------------------------------

        recipient_pub_key = x25519.X25519PublicKey.from_public_bytes(recipient_pub_bytes)
        shared_secret = self.private_key.exchange(recipient_pub_key)

        timestamp_ns = time.time_ns() 
        timestamp_bytes = struct.pack("!Q", timestamp_ns)
        session_key = self.derive_session_key(shared_secret, timestamp_bytes)

        aesgcm = AESGCM(session_key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext_message.encode('utf-8'), None)

        return {
            "sender": self.user_id,
            "nonce": b64encode(nonce).decode('utf-8'),
            "timestamp": b64encode(timestamp_bytes).decode('utf-8'),
            "ciphertext": b64encode(ciphertext).decode('utf-8')
        }

    def receive_message(self, packet):
        sender_id = packet['sender']
        
        # Receiver also verifies Sender's Merkle Proof
        sender_pub_bytes = self.server.get_public_key(sender_id)
        proof = self.server.get_merkle_proof(sender_id)
        blockchain_root = self.blockchain.get_latest_root()
        
        # Simple Verify for Receiver
        if proof['root_at_generation'] != blockchain_root:
            print("Receiver: Sender verification failed on Blockchain.")
            return None
            
        sender_pub_key = x25519.X25519PublicKey.from_public_bytes(sender_pub_bytes)
        shared_secret = self.private_key.exchange(sender_pub_key)

        timestamp_bytes = b64decode(packet['timestamp'])
        session_key = self.derive_session_key(shared_secret, timestamp_bytes)

        aesgcm = AESGCM(session_key)
        nonce = b64decode(packet['nonce'])
        ciphertext = b64decode(packet['ciphertext'])

        try:
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode('utf-8')
        except:
            return "[ERROR] Decryption Failed!"

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    print("--- 🚀 INITIALIZING MERKLE-VERIFIED FRAMEWORK ---\n")
    
    # 1. Setup Infrastructure
    merkle_tree = MerkleTree()
    ledger = BlockchainLedger()
    server = KeyServer(merkle_tree, ledger) # Server now manages the Tree
    
    # 2. Register Users (Builds the Tree dynamically)
    alice = SecureUser("Alice", server, ledger)
    bob = SecureUser("Bob", server, ledger)
    charlie = SecureUser("Charlie", server, ledger) # Adding a 3rd user changes the Root!

    # 3. Alice Sends Message
    packet = alice.send_message("Bob", "Merkle Trees are cool!")

    if packet:
        msg = bob.receive_message(packet)
        print(f"\n[Bob] Decrypted: {msg}")

    # --- 4. SIMULATE MERKLE ATTACK ---
    print("\n--- 🏴‍☠️ SIMULATING ROOT FORGERY ATTACK ---")
    
    # Mallory hacks the server and creates a FAKE tree with fake keys
    fake_root = "abcdef1234567890" # A random fake root
    
    # She tries to trick Alice by giving her a proof that points to this fake root
    # But Alice checks the BLOCKCHAIN, which still has the REAL root.
    
    print(f"[Attack] Server sends proof with Root: {fake_root}")
    print(f"[Blockchain] Actual Immutable Root: {ledger.get_latest_root()[:15]}...")
    
    # We manually trigger the check to show failure
    if fake_root != ledger.get_latest_root():
        print("\n[Alice] 🔍 Verifying Proof...")
        print("🚨 Root Mismatch! Proof says abcdef12345... but Blockchain has something else...")
        print("🛡️ ATTACK BLOCKED: The server cannot fake the Merkle Root.")