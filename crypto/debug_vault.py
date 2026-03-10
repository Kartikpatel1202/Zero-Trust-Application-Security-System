import os, sys, requests, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

URL = os.environ["SUPABASE_URL"]
KEY = os.environ["SUPABASE_KEY"]

H_STORAGE = {
    "apikey": KEY,
    "Authorization": "Bearer " + KEY,
    "Content-Type": "application/json",
}

endpoint = URL + "/storage/v1/object/list/secure_vault"

print("=" * 60)
print("TEST 1: List root of secure_vault (empty prefix)")
print("=" * 60)
r = requests.post(endpoint, headers=H_STORAGE, json={"prefix": "", "limit": 100, "offset": 0})
print("Status:", r.status_code)
try:
    print("Response:", json.dumps(r.json(), indent=2))
except Exception:
    print("Raw:", r.text)

print()
for user in ["yash", "yash2", "divya"]:
    print("TEST 2: List prefix='" + user + "/'")
    r2 = requests.post(endpoint, headers=H_STORAGE, json={
        "prefix": user + "/", "limit": 100, "offset": 0,
        "sortBy": {"column": "name", "order": "asc"}
    })
    print("  Status:", r2.status_code)
    try:
        items = r2.json()
        print("  Items count:", len(items))
        print("  Items:", json.dumps(items, indent=2))
    except Exception:
        print("  Raw:", r2.text)
    print()

print("=" * 60)
print("TEST 3: List root WITH Prefer header (DB-only header)")
print("=" * 60)
H_DB = dict(H_STORAGE)
H_DB["Prefer"] = "return=representation"
r3 = requests.post(endpoint, headers=H_DB, json={"prefix": "", "limit": 100, "offset": 0})
print("Status:", r3.status_code)
try:
    print("Response:", json.dumps(r3.json(), indent=2))
except Exception:
    print("Raw:", r3.text)
