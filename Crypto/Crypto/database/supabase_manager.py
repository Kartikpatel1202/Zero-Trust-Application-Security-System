import os
import requests
from dotenv import load_dotenv

load_dotenv()

class SupabaseManager:
    def __init__(self):
        self.url = os.environ.get("SUPABASE_URL")
        self.key = os.environ.get("SUPABASE_KEY")
        
        if not self.url or not self.key:
            raise ValueError("🚨 Missing Supabase credentials in .env file!")
            
        # These headers are required by the Supabase REST API
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        print("[Database] ☁️ Connected to Supabase via REST API.")

    # --- 1. IDENTITY LAYER ---
    def register_user(self, username, pub_key_hex, leaf_hash):
        endpoint = f"{self.url}/rest/v1/users"
        data = {
            "username": username,
            "public_key_hex": pub_key_hex,
            "merkle_leaf_hash": leaf_hash,
            "trust_score": 100
        }
        response = requests.post(endpoint, headers=self.headers, json=data)
        
        if response.status_code in [200, 201]:
            return True
        print(f"[Supabase] Error registering: {response.text}")
        return False

    def get_user(self, username):
        endpoint = f"{self.url}/rest/v1/users?username=eq.{username}&select=*"
        response = requests.get(endpoint, headers=self.headers)
        
        if response.status_code == 200 and len(response.json()) > 0:
            user = response.json()[0]
            return (user['public_key_hex'], user['merkle_leaf_hash'], user['trust_score'])
        return None
    def get_all_users(self):
        """Used by the Server to rebuild the Merkle Tree deterministically."""
        # 🔥 FIX: Added &order=username.asc so the Merkle Tree is identical on all computers!
        endpoint = f"{self.url}/rest/v1/users?select=username,public_key_hex&order=username.asc"
        response = requests.get(endpoint, headers=self.headers)
        
        if response.status_code == 200:
            return response.json()
        return []
        return []
    # --- 2. THE HANDSHAKE LAYER ---
    def request_connection(self, requester, receiver):
        endpoint = f"{self.url}/rest/v1/connections"
        data = {
            "requester_username": requester,
            "receiver_username": receiver,
            "status": "pending_verification"
        }
        response = requests.post(endpoint, headers=self.headers, json=data)
        if response.status_code in [200, 201]:
            print(f"[Supabase] 🤝 Connection request sent to {receiver}.")
            return True
        return False

    def verify_connection(self, requester, receiver):
        endpoint = f"{self.url}/rest/v1/connections?requester_username=eq.{requester}&receiver_username=eq.{receiver}"
        data = {"status": "verified"}
        response = requests.patch(endpoint, headers=self.headers, json=data)
        if response.status_code in [200, 204]:
            print(f"[Supabase] ✅ Connection between {requester} and {receiver} is Verified.")
            return True
        return False

    def check_connection_status(self, user1, user2):
        # Check direction 1
        endpoint1 = f"{self.url}/rest/v1/connections?requester_username=eq.{user1}&receiver_username=eq.{user2}&select=status"
        res1 = requests.get(endpoint1, headers=self.headers).json()
        
        # Check direction 2
        endpoint2 = f"{self.url}/rest/v1/connections?requester_username=eq.{user2}&receiver_username=eq.{user1}&select=status"
        res2 = requests.get(endpoint2, headers=self.headers).json()
        
        if (len(res1) > 0 and res1[0].get('status') == 'verified') or \
           (len(res2) > 0 and res2[0].get('status') == 'verified'):
            return True
        return False

    # --- 3. THE DATA LAYER ---
    def store_message(self, sender, recipient, ciphertext, nonce, timestamp):
        if not self.check_connection_status(sender, recipient):
            print(f"[Supabase] 🚨 BLOCKED: No verified connection!")
            return False

        endpoint = f"{self.url}/rest/v1/messages"
        data = {
            "sender_username": sender,
            "recipient_username": recipient,
            "ciphertext_b64": ciphertext,
            "nonce_b64": nonce,
            "timestamp_b64": timestamp
        }
        response = requests.post(endpoint, headers=self.headers, json=data)
        return response.status_code in [200, 201]

    def get_messages_for(self, username):
        endpoint = f"{self.url}/rest/v1/messages?recipient_username=eq.{username}&select=*"
        response = requests.get(endpoint, headers=self.headers)
        
        formatted_msgs = []
        if response.status_code == 200:
            for msg in response.json():
                formatted_msgs.append((
                    msg.get('id'), msg.get('sender_username'), msg.get('recipient_username'), 
                    msg.get('ciphertext_b64'), msg.get('nonce_b64'), msg.get('timestamp_b64'), 'unread'
                ))
        return formatted_msgs