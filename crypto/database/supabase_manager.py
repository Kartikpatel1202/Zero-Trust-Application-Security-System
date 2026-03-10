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
            
        # Headers for Supabase PostgREST (database) API
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        # Headers for Supabase Storage API — NO 'Prefer' header (PostgREST-only)
        self.storage_headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
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
        endpoint = f"{self.url}/rest/v1/users?select=username,public_key_hex&order=username.asc"
        response = requests.get(endpoint, headers=self.headers)
        
        if response.status_code == 200:
            return response.json()
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

    def get_pending_requests(self, username):
        """Fetches pending connection requests for the given user."""
        endpoint = f"{self.url}/rest/v1/connections?receiver_username=eq.{username}&status=eq.pending_verification&select=requester_username"
        response = requests.get(endpoint, headers=self.headers)
        if response.status_code == 200:
            return [row.get("requester_username") for row in response.json()]
        return []

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

    def delete_messages_between(self, user1, user2):
        """Permanently deletes all messages between user1 and user2."""
        # Delete where user1 is sender and user2 is recipient
        end1 = f"{self.url}/rest/v1/messages?sender_username=eq.{user1}&recipient_username=eq.{user2}"
        requests.delete(end1, headers=self.headers)
        
        # Delete where user2 is sender and user1 is recipient
        end2 = f"{self.url}/rest/v1/messages?sender_username=eq.{user2}&recipient_username=eq.{user1}"
        requests.delete(end2, headers=self.headers)
        
        print(f"[Supabase] 🗑️ Wiped FULL conversation tracking between {user1} and {user2}.")
        return True

    def get_messages_between(self, user1, user2):
        """Fetches all messages between two users in both directions."""
        end1 = f"{self.url}/rest/v1/messages?sender_username=eq.{user1}&recipient_username=eq.{user2}&select=*"
        res1 = requests.get(end1, headers=self.headers).json()
        
        end2 = f"{self.url}/rest/v1/messages?sender_username=eq.{user2}&recipient_username=eq.{user1}&select=*"
        res2 = requests.get(end2, headers=self.headers).json()
        
        if isinstance(res1, list) and isinstance(res2, list):
            return res1 + res2
        return []

    def delete_messages_by_ids(self, msg_ids):
        """Permanently deletes messages by their IDs."""
        if not msg_ids: return True
        ids_str = ",".join(msg_ids)
        endpoint = f"{self.url}/rest/v1/messages?id=in.({ids_str})"
        response = requests.delete(endpoint, headers=self.headers)
        print(f"[Supabase] 🗑️ Wiped {len(msg_ids)} specific BURN messages.")
        return response.status_code in [200, 204]

    # --- 4. THE STORAGE LAYER (secure_vault) ---
    def upload_file(self, file_content, remote_path):
        """Uploads encrypted file content to the secure_vault bucket.
        Uses x-upsert: true so overwriting an existing file doesn't fail with 400."""
        endpoint = f"{self.url}/storage/v1/object/secure_vault/{remote_path}"
        upload_headers = self.storage_headers.copy()
        upload_headers["Content-Type"] = "application/octet-stream"
        upload_headers["x-upsert"] = "true"  # allow overwrite without conflict error
        response = requests.post(endpoint, headers=upload_headers, data=file_content)
        if 200 <= response.status_code < 300:
            return True
        print(f"[Supabase Storage] Upload failed — HTTP {response.status_code}: {response.text}")
        return False

    def download_file(self, remote_path):
        """Downloads a file from the secure_vault bucket."""
        endpoint = f"{self.url}/storage/v1/object/secure_vault/{remote_path}"
        response = requests.get(endpoint, headers=self.storage_headers)
        if response.status_code == 200:
            return response.content
        print(f"[Supabase Storage] Download failed — HTTP {response.status_code}: {response.text}")
        return None

    def list_vault_files(self, prefix=""):
        """Lists files in the secure_vault bucket under the given prefix folder."""
        endpoint = f"{self.url}/storage/v1/object/list/secure_vault"
        # Use 'name' sort — always supported; avoid 'created_at' which may not work on all plans
        data = {"prefix": prefix, "limit": 100, "offset": 0,
                "sortBy": {"column": "name", "order": "asc"}}
        response = requests.post(endpoint, headers=self.storage_headers, json=data)
        if response.status_code == 200:
            files = response.json()
            # Filter out placeholder/folder entries (id is None)
            return [f for f in files if f.get("id") is not None]
        print(f"[Supabase Storage] List failed — HTTP {response.status_code}: {response.text}")
        return []

    def list_sent_files(self, sender_username):
        """Lists all files uploaded by sender_username across all recipient folders.
        Files are stored as {recipient}/{sender}_{filename}.enc — we scan all top-level
        folders and filter by name prefix."""
        all_files = []
        endpoint = f"{self.url}/storage/v1/object/list/secure_vault"
        # Get all top-level folder names (recipients)
        data = {"prefix": "", "limit": 100, "offset": 0,
                "sortBy": {"column": "name", "order": "asc"}}
        resp = requests.post(endpoint, headers=self.storage_headers, json=data)
        if resp.status_code != 200:
            return []

        folders = resp.json()
        for folder in folders:
            folder_name = folder.get("name", "")
            if not folder_name:
                continue
            # List files inside each recipient folder
            inner_data = {"prefix": f"{folder_name}/", "limit": 100, "offset": 0,
                          "sortBy": {"column": "name", "order": "asc"}}
            inner_resp = requests.post(endpoint, headers=self.storage_headers, json=inner_data)
            if inner_resp.status_code == 200:
                for f in inner_resp.json():
                    fname = f.get("name", "")
                    # Filter: file names are {sender}_{original}.enc
                    if fname.startswith(f"{sender_username}_"):
                        f["_recipient"] = folder_name
                        f["_remote_path"] = f"{folder_name}/{fname}"
                        all_files.append(f)
        return all_files

    def get_verified_contacts(self, username):
        """Returns list of usernames who have a verified connection with username.
        Note: the 'status' column stores 'verified' (set by verify_connection)."""
        endpoint1 = f"{self.url}/rest/v1/connections?requester_username=eq.{username}&status=eq.verified&select=receiver_username"
        endpoint2 = f"{self.url}/rest/v1/connections?receiver_username=eq.{username}&status=eq.verified&select=requester_username"
        contacts = set()
        r1 = requests.get(endpoint1, headers=self.headers)
        if r1.status_code == 200:
            for row in r1.json():
                contacts.add(row.get("receiver_username", ""))
        r2 = requests.get(endpoint2, headers=self.headers)
        if r2.status_code == 200:
            for row in r2.json():
                contacts.add(row.get("requester_username", ""))
        contacts.discard("")
        return sorted(contacts)
