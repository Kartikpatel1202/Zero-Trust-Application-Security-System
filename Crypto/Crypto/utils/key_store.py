"""
Local key storage for the Secure Messenger interface.
Stores private keys on disk so users can decrypt messages across app restarts.
"""
import os

# Keys stored in project root / keys / {username}.key
def _get_keys_dir():
    current = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current)
    keys_dir = os.path.join(project_root, "keys")
    os.makedirs(keys_dir, exist_ok=True)
    return keys_dir

def get_key_path(username):
    return os.path.join(_get_keys_dir(), f"{username}.key")

def save_private_key(username, private_key_bytes):
    """Save private key to local file (hex-encoded)."""
    path = get_key_path(username)
    with open(path, "w") as f:
        f.write(private_key_bytes.hex())
    return path

def load_private_key(username):
    """Load private key from local file. Returns bytes or None if not found."""
    path = get_key_path(username)
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        hex_data = f.read().strip()
    return bytes.fromhex(hex_data)

def has_key(username):
    """Check if a key file exists for this user."""
    return os.path.exists(get_key_path(username))

