import os
import time
import struct
from base64 import b64encode, b64decode
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class CryptoEngine:
    def __init__(self, private_key_bytes=None):
        """
        Initializes the cryptographic engine.
        Generates new X25519 keys if none are provided.
        """
        if private_key_bytes:
            self.private_key = x25519.X25519PrivateKey.from_private_bytes(private_key_bytes)
        else:
            self.private_key = x25519.X25519PrivateKey.generate()
            
        self.public_key = self.private_key.public_key()

    def get_public_bytes(self):
        """Returns the public key in raw bytes format."""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )

    def get_private_bytes(self):
        """Returns the private key in raw bytes format (for local persistence)."""
        return self.private_key.private_bytes_raw()

    # --- 🔥 YOUR NOVELTY LIVES HERE 🔥 ---
    def derive_bound_session_key(self, shared_secret, timestamp_bytes, merkle_root_bytes):
        """
        Generates a symmetric AES key by combining:
        1. X3DH Shared Secret (Standard)
        2. High-Precision Timestamp (Prevents Replay Attacks)
        3. Merkle Root (Cryptographically binds identity verification to the key)
        """
        # The key material is a fusion of all three elements
        input_key_material = shared_secret + timestamp_bytes + merkle_root_bytes
        
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32, # 256-bit key for AES-256
            salt=None, 
            info=b'Time-Identity-Bound-Key', # Context label
        )
        return hkdf.derive(input_key_material)
    # ------------------------------------

    def encrypt(self, plaintext_message, recipient_pub_bytes, blockchain_root_bytes):
        """
        Executes the end-to-end encryption workflow.
        """
        # 1. Standard X3DH
        recipient_pub_key = x25519.X25519PublicKey.from_public_bytes(recipient_pub_bytes)
        shared_secret = self.private_key.exchange(recipient_pub_key)

        # 2. Timestamp Generation
        timestamp_ns = time.time_ns() 
        timestamp_bytes = struct.pack("!Q", timestamp_ns)

        # 3. Novel Key Derivation
        session_key = self.derive_bound_session_key(shared_secret, timestamp_bytes, blockchain_root_bytes)

        # 4. AES-GCM Encryption
        aesgcm = AESGCM(session_key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext_message.encode('utf-8'), None)

        # Return the components needed for the network packet
        return {
            "nonce_b64": b64encode(nonce).decode('utf-8'),
            "timestamp_b64": b64encode(timestamp_bytes).decode('utf-8'),
            "ciphertext_b64": b64encode(ciphertext).decode('utf-8')
        }

    def decrypt(self, ciphertext_b64, nonce_b64, timestamp_b64, sender_pub_bytes, blockchain_root_bytes):
        """
        Executes the decryption workflow, enforcing the Blockchain Root check.
        """
        # 1. Decode payloads
        nonce = b64decode(nonce_b64)
        timestamp_bytes = b64decode(timestamp_b64)
        ciphertext = b64decode(ciphertext_b64)

        # 2. Standard X3DH
        sender_pub_key = x25519.X25519PublicKey.from_public_bytes(sender_pub_bytes)
        shared_secret = self.private_key.exchange(sender_pub_key)

        # 3. Derive Key (Will fail if the local blockchain_root_bytes doesn't match the sender's)
        session_key = self.derive_bound_session_key(shared_secret, timestamp_bytes, blockchain_root_bytes)

        # 4. AES-GCM Decryption
        aesgcm = AESGCM(session_key)
        try:
            plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext_bytes.decode('utf-8')
        except Exception as e:
            raise Exception(f"Decryption failed! Root mismatch or tampered data. Details: {e}")

    def encrypt_file(self, file_bytes, recipient_pub_bytes, blockchain_root_bytes):
        """
        Encrypts a file (bytes) using the same Time-Identity-Bound logic as messages.
        """
        recipient_pub_key = x25519.X25519PublicKey.from_public_bytes(recipient_pub_bytes)
        shared_secret = self.private_key.exchange(recipient_pub_key)
        timestamp_ns = time.time_ns() 
        timestamp_bytes = struct.pack("!Q", timestamp_ns)
        session_key = self.derive_bound_session_key(shared_secret, timestamp_bytes, blockchain_root_bytes)
        aesgcm = AESGCM(session_key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, file_bytes, None)
        return nonce + timestamp_bytes + ciphertext

    def decrypt_file(self, encrypted_file_bytes, sender_pub_bytes, blockchain_root_bytes):
        """
        Decrypts a file (bytes) using the same Time-Identity-Bound logic as messages.
        """
        if len(encrypted_file_bytes) < 20:
            raise Exception("Invalid encrypted file format")
        nonce = encrypted_file_bytes[:12]
        timestamp_bytes = encrypted_file_bytes[12:20]
        ciphertext = encrypted_file_bytes[20:]
        sender_pub_key = x25519.X25519PublicKey.from_public_bytes(sender_pub_bytes)
        shared_secret = self.private_key.exchange(sender_pub_key)
        session_key = self.derive_bound_session_key(shared_secret, timestamp_bytes, blockchain_root_bytes)
        aesgcm = AESGCM(session_key)
        try:
            return aesgcm.decrypt(nonce, ciphertext, None)
        except Exception as e:
            raise Exception(f"File decryption failed! Root mismatch or tampered data. Details: {e}")
