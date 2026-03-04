import requests
import os
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json"
}

print("[System] Wiping all ghost users and old messages from Supabase...")

# Delete everything
requests.delete(f"{url}/rest/v1/messages?id=not.is.null", headers=headers)
requests.delete(f"{url}/rest/v1/connections?id=not.is.null", headers=headers)
requests.delete(f"{url}/rest/v1/users?id=not.is.null", headers=headers)

print("[System] ✅ Database is 100% clean! You are ready for a fresh run.")