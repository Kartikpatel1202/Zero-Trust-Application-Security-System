import hashlib

class MerkleTree:
    def __init__(self):
        # A list to store individual user hashes
        self.leaves = [] 
        self.root = b''

    def rebuild_from_users(self, users_list):
        """
        Rebuild tree from scratch in exact order. Ensures identical root across
        all app instances (Yash & Divya must derive same session key).
        users_list: [(username, public_key_bytes), ...] in deterministic order
        """
        self.leaves = []
        for user_id, public_key_bytes in users_list:
            leaf_hash = hashlib.blake2b(public_key_bytes, digest_size=32).hexdigest()
            self.leaves.append({"id": user_id, "hash": leaf_hash})
        self.recalculate_root()

    def add_leaf(self, user_id, public_key_bytes):
        """
        Hashes the user's public key and adds it to the tree.
        """
        # Using BLAKE2b (faster and more secure than standard SHA-256)
        leaf_hash = hashlib.blake2b(public_key_bytes, digest_size=32).hexdigest()
        
        # Check if user already exists in leaves to prevent duplicates
        for leaf in self.leaves:
            if leaf["id"] == user_id:
                # Update existing leaf
                leaf["hash"] = leaf_hash
                self.recalculate_root()
                return leaf_hash

        # Add new leaf
        self.leaves.append({"id": user_id, "hash": leaf_hash})
        self.recalculate_root()
        return leaf_hash

    def recalculate_root(self):
        """
        Rebuilds the Merkle Root from all current leaves.
        """
        if not self.leaves:
            self.root = b''
            return

        # Start with the bottom layer (all user hashes converted back to bytes)
        current_level = [bytes.fromhex(item["hash"]) for item in self.leaves]
        
        # Pair up and hash until only 1 node remains (The Root)
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                # If an odd number of leaves, duplicate the last one
                right = current_level[i+1] if (i+1) < len(current_level) else left
                
                # Combine Left + Right and Hash
                combined = left + right
                new_hash = hashlib.blake2b(combined, digest_size=32).digest()
                next_level.append(new_hash)
            
            current_level = next_level
        
        self.root = current_level[0]
        print(f"[Merkle System] 🌳 Tree Rebuilt. New Root: {self.root.hex()[:10]}...")

    def get_proof(self, user_id):
        """
        Generates the proof required for a client to verify a user.
        Includes the Leaf Hash and the Global Root it belongs to.
        """
        for leaf in self.leaves:
            if leaf["id"] == user_id:
                return {
                    "leaf_hash": leaf["hash"],
                    "global_root_hex": self.root.hex()
                }
        return None