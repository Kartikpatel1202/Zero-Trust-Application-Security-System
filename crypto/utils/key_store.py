"""
Local key storage for the Secure Messenger interface.
Stores private keys on disk so users can decrypt messages across app restarts.
"""
import os
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

# Keys stored in project root / keys / {username}.key
def _get_keys_dir():
    current = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current)
    keys_dir = os.path.join(project_root, "keys")
    os.makedirs(keys_dir, exist_ok=True)
    return keys_dir

def _derive_key(password, salt):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    return kdf.derive(password.encode())

def get_key_path(username):
    return os.path.join(_get_keys_dir(), f"{username}.key")

def save_private_key(username, private_key_bytes, password):
    """Save private key to local file (encrypted with password)."""
    salt = os.urandom(16)
    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, private_key_bytes, None)
    
    path = get_key_path(username)
    with open(path, "wb") as f:
        f.write(salt + nonce + ciphertext)
    return path

def load_private_key(username, password):
    """Load private key from local file. Returns bytes or None if not found, False if wrong password."""
    path = get_key_path(username)
    if not os.path.exists(path):
        return None
    
    try:
        with open(path, "rb") as f:
            data = f.read()
        
        salt = data[:16]
        nonce = data[16:28]
        ciphertext = data[28:]
        
        key = _derive_key(password, salt)
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, None)
    except Exception:
        return False

def has_key(username):
    """Check if a key file exists for this user."""
    return os.path.exists(get_key_path(username))

