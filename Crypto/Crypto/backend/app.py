from flask import Flask, request, jsonify
from flask_cors import CORS
from functools import wraps
import os
import sys
import json
import base64
import requests

# Project root and path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
from supabase import create_client, Client
import base64
from supabase import create_client, Client
# Load .env from project root
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_ROOT, ".env"))
except ImportError:
    pass

from network.server import ZTAServer
from network.client import SecureClient
from database.supabase_manager import SupabaseManager

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000", "http://localhost:5173"])

# Supabase Auth via REST API (no supabase package = no httpx/httpcore)
supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
supabase_key = os.environ.get("SUPABASE_KEY", "")
supabase_auth_headers = {
    "apikey": supabase_key,
    "Authorization": f"Bearer {supabase_key}",
    "Content-Type": "application/json",
}

# Initialize ZTA Server
zta_server = ZTAServer()

# Store active client sessions (in production, use Redis or similar)
active_clients = {}
# Store token to email mapping (in production, use JWT decoding)
        # Check our token mapping first
token_to_email = {}
        # Check our token mapping first

def get_user_from_token():
    """Extract user from Supabase JWT token"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None
    
    try:
        token = auth_header.replace('Bearer ', '')
        
        # Alternative: Store user email in a simple way
        # For production, use proper JWT verification
        # For now, we'll use a simpler approach - store email in token or session
        if token in token_to_email:
            email = token_to_email[token]
            class _User:
                def __init__(self, email):
                    self.email = email
            return _User(email)
        return None
    except Exception as e:
        print(f"Auth error: {e}")
        return None

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_user_from_token()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401
        
        # Get or create SecureClient for this user
        username = user.email.split('@')[0]  # Use email prefix as username
        if username not in active_clients:
            active_clients[username] = SecureClient(username, zta_server)
            # Check if user is registered, if not, register them
            if not zta_server.db.get_user(username):
                active_clients[username].register()
        
        request.current_user = user
        request.username = username
        request.client = active_clients[username]
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user with Supabase Auth REST API"""
    data = request.json
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({"error": "email and password required"}), 400
    try:
        r = requests.post(
            f"{supabase_url}/auth/v1/signup",
            headers=supabase_auth_headers,
            json={"email": email, "password": password},
            timeout=10,
        )
        body = r.json() if r.text else {}
        if r.status_code in (200, 201):
            return jsonify({"message": "Registration successful", "user": email}), 201
        return jsonify({"error": body.get("msg", body.get("error_description", r.text))}), r.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login with Supabase Auth REST API"""
    data = request.json
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({"error": "email and password required"}), 400
    try:
        r = requests.post(
            f"{supabase_url}/auth/v1/token?grant_type=password",
            headers=supabase_auth_headers,
            json={"email": email, "password": password},
            timeout=10,
        )
            # Register if not exists
        body = r.json() if r.text else {}
        
        # Perform ZTA login
        if r.status_code != 200:
            # Register if not exists
            return jsonify({"error": body.get("error_description", body.get("msg", r.text))}), r.status_code
        
        # Perform ZTA login
        access_token = body.get("access_token")
        user_obj = body.get("user") or {}
        if not access_token:
            return jsonify({"error": "No access token in response"}), 401
        username = (user_obj.get("email") or email).split("@")[0]
        device_context = {"is_rooted": False, "location": "Web_Browser"}
        if username not in active_clients:
            active_clients[username] = SecureClient(username, zta_server)
            if not zta_server.db.get_user(username):
                active_clients[username].register()
        login_success = active_clients[username].login(device_context)
        if not login_success:
            return jsonify({"error": "ZTA authentication failed"}), 403
        token_to_email[access_token] = user_obj.get("email") or email
        return jsonify({
            "access_token": access_token,
            "user": {"email": user_obj.get("email") or email, "username": username},
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 401

@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout():
    """Clear server-side session; frontend should clear Supabase session."""
    try:
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.replace("Bearer ", "")
            token_to_email.pop(token, None)
        username = getattr(request, "username", None)
        if username and username in active_clients:
            del active_clients[username]
        return jsonify({"message": "Logged out successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/users/me', methods=['GET'])
@require_auth
def get_current_user():
    """Get current user info"""
    return jsonify({
        "username": request.username,
        "email": request.current_user.email
    }), 200

@app.route('/api/users', methods=['GET'])
@require_auth
def get_all_users():
    """Get all registered users"""
    users = zta_server.db.get_all_users()
    # Filter out current user
    filtered_users = [
        {"username": u['username'], "public_key_hex": u['public_key_hex'][:20] + "..."}
        for u in users if u['username'] != request.username
    ]
    return jsonify({"users": filtered_users}), 200

@app.route('/api/connections/request', methods=['POST'])
@require_auth
def request_connection():
    """Request a connection with another user"""
    data = request.json
    target_username = data.get('target_username')
    
    if not target_username:
        return jsonify({"error": "target_username required"}), 400
    
    try:
        request.client.request_connection(target_username)
        return jsonify({"message": f"Connection request sent to {target_username}"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/connections/pending', methods=['GET'])
@require_auth
def get_pending_connections():
    """Get pending connection requests"""
    db = zta_server.db
    endpoint = f"{db.url}/rest/v1/connections?receiver_username=eq.{request.username}&status=eq.pending_verification&select=*"
    response = requests.get(endpoint, headers=db.headers)
    
    if response.status_code == 200:
        requests_list = response.json()
        return jsonify({"pending_requests": requests_list}), 200
    return jsonify({"pending_requests": []}), 200

@app.route('/api/connections/accept', methods=['POST'])
@require_auth
def accept_connection():
    """Accept a connection request"""
    data = request.json
    requester_username = data.get('requester_username')
    
    if not requester_username:
        return jsonify({"error": "requester_username required"}), 400
    
    try:
        request.client.verify_and_accept_connection(requester_username)
        return jsonify({"message": f"Connection established with {requester_username}"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/connections', methods=['GET'])
@require_auth
def get_connections():
    """Get all verified connections"""
    db = zta_server.db
    # Get connections where user is requester
    endpoint1 = f"{db.url}/rest/v1/connections?requester_username=eq.{request.username}&status=eq.verified&select=*"
    res1 = requests.get(endpoint1, headers=db.headers)
    
    # Get connections where user is receiver
    endpoint2 = f"{db.url}/rest/v1/connections?receiver_username=eq.{request.username}&status=eq.verified&select=*"
    res2 = requests.get(endpoint2, headers=db.headers)
    
    connections = []
    if res1.status_code == 200:
        connections.extend(res1.json())
    if res2.status_code == 200:
        connections.extend(res2.json())
    
    # Extract unique usernames
    connected_users = set()
    for conn in connections:
        if conn['requester_username'] == request.username:
            connected_users.add(conn['receiver_username'])
        else:
            connected_users.add(conn['requester_username'])
    
    return jsonify({"connections": list(connected_users)}), 200

@app.route('/api/messages/send', methods=['POST'])
@require_auth
def send_message():
    """Send an encrypted message"""
    data = request.json
    recipient_username = data.get('recipient_username')
    message = data.get('message')
    
    if not recipient_username or not message:
        return jsonify({"error": "recipient_username and message required"}), 400
    
    try:
        request.client.send_message(recipient_username, message)
        return jsonify({"message": "Message sent successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/messages', methods=['GET'])
@require_auth
def get_messages():
    """Get all messages for current user"""
    try:
        # Get raw messages from database
        db = zta_server.db
        raw_messages = db.get_messages_for(request.username)
        
        formatted_messages = []
        for msg in raw_messages:
            msg_id, sender, recipient, ciphertext_b64, nonce_b64, timestamp_b64, status = msg
            # Decrypt message
            try:
                sender_data = zta_server.get_client_data(sender)
                blockchain_root_bytes = zta_server.get_blockchain_root()
                plaintext = request.client.crypto_engine.decrypt(
                    ciphertext_b64, nonce_b64, timestamp_b64,
                    sender_data["public_key_bytes"], blockchain_root_bytes
                )
                formatted_messages.append({
                    "id": msg_id,
                    "sender": sender,
                    "recipient": recipient,
                    "message": plaintext,
                    "timestamp": timestamp_b64
                })
            except Exception as e:
                formatted_messages.append({
                    "id": msg_id,
                    "sender": sender,
                    "recipient": recipient,
                    "message": f"[Decryption failed: {str(e)}]",
                    "timestamp": timestamp_b64
                })
        
        return jsonify({"messages": formatted_messages}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/files/upload', methods=['POST'])
@require_auth
def upload_file():
    """Upload and encrypt a file"""
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    recipient_username = request.form.get('recipient_username')
    if not recipient_username:
        return jsonify({"error": "recipient_username required"}), 400
    
    file = request.files['file']
    file_data = file.read()
    
    try:
        # Encrypt file data as message
        recipient_data = zta_server.get_client_data(recipient_username)
        blockchain_root_bytes = zta_server.get_blockchain_root()
        
        # Convert file to base64 string for encryption
        file_b64 = base64.b64encode(file_data).decode('utf-8')
        file_message = f"FILE:{file.filename}:{file_b64}"
        
        packet = request.client.crypto_engine.encrypt(
            file_message, 
            recipient_data["public_key_bytes"], 
            blockchain_root_bytes
        )
        
        # Store encrypted file
        zta_server.route_message(request.username, recipient_username, packet)
        
        return jsonify({
            "message": "File uploaded and encrypted successfully",
            "filename": file.filename
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)
