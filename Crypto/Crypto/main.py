import time
from network.server import ZTAServer
from network.client import SecureClient

def run_demonstration():
    print("="*60)
    print("🚀 STARTING CLOUD-NATIVE ZERO TRUST FRAMEWORK 🚀")
    print("="*60)

    print("\n--- [PHASE 1] CONNECTING TO SUPABASE & BLOCKCHAIN ---")
    server = ZTAServer() 
    
    print("\n--- [PHASE 2] REGISTRATION ---")
    alice = SecureClient("Alice", server)
    bob = SecureClient("Bob", server)
    
    alice.register()
    bob.register()

    print("\n--- [PHASE 3] ZERO TRUST LOGIN ---")
    alice.login({"is_rooted": False, "location": "Headquarters"})
    bob.login({"is_rooted": False, "location": "Branch_Office"})

    print("\n--- [PHASE 4] THE HANDSHAKE (NOVELTY) ---")
    print("[System] Initiating Cryptographic Handshake...")
    alice.request_connection("Bob")
    bob.verify_and_accept_connection("Alice")

    print("\n--- [PHASE 5] SECURE DATA TRANSMISSION ---")
    # 🔥 THIS IS THE NEW INTERACTIVE PART 🔥
    print("\n" + "-"*40)
    user_message = input("👉 Type a secret message for Bob: ")
    print("-"*40 + "\n")
    
    print("[System] Alice encrypting and sending message...")
    alice.send_message("Bob", user_message)

    print("[System] Waiting for cloud network sync...")
    time.sleep(1.5)

    print("\n--- [PHASE 6] RECEPTION & DECRYPTION ---")
    bob.check_inbox()

    print("\n" + "="*60)
    print("✅ DEMONSTRATION COMPLETE: SYSTEM FULLY SECURE ✅")
    print("="*60)

if __name__ == "__main__":
    # Clean up the DB automatically using the REST API
    import requests
    print("[System] Wiping previous cloud data for a fresh run...")
    server = ZTAServer()
    
    # Delete all rows in the tables so Alice and Bob can generate fresh keys
    requests.delete(f"{server.db.url}/rest/v1/messages?id=not.is.null", headers=server.db.headers)
    requests.delete(f"{server.db.url}/rest/v1/connections?id=not.is.null", headers=server.db.headers)
    requests.delete(f"{server.db.url}/rest/v1/users?id=not.is.null", headers=server.db.headers)
    
    # Run the interactive demo
    run_demonstration()