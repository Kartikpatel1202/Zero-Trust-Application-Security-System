# Zero Trust Secure Messaging Platform

A complete end-to-end encrypted messaging application with Merkle tree verification and XDH key exchange.

## Features

- 🔐 **Zero Trust Authentication** - Device context verification
- 🌳 **Merkle Tree Identity Verification** - Cryptographic proof of identity
- 🔑 **XDH Key Exchange** - Secure key derivation using X25519
- 💬 **End-to-End Encrypted Messaging** - Messages encrypted with AES-GCM
- 📎 **Secure File Transfer** - Encrypted file upload and download
- 🤝 **Connection Handshake** - Verified connections before messaging
- ☁️ **Supabase Integration** - Cloud database and authentication

## Architecture

- **Backend**: Flask API server wrapping the encryption logic
- **Frontend**: React application with modern UI
- **Database**: Supabase (PostgreSQL)
- **Encryption**: X25519 (XDH) + AES-GCM + Merkle Tree verification

## Setup Instructions

### Prerequisites

- Python 3.8+
- Node.js 18+
- Supabase account and project

### Backend Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables in `.env`:
```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

3. Start the Flask server:
```bash
cd backend
python app.py
```

The backend will run on `http://localhost:5000`

### Frontend Setup

1. Install Node dependencies:
```bash
cd frontend
npm install
```

2. Configure environment variables (optional, defaults are set):
Create `frontend/.env`:
```
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
```

3. Start the development server:
```bash
npm run dev
```

The frontend will run on `http://localhost:3000`

### Supabase Database Schema

Make sure your Supabase project has these tables:

**users**:
- id (uuid, primary key)
- username (text, unique)
- public_key_hex (text)
- merkle_leaf_hash (text)
- trust_score (integer)

**connections**:
- id (uuid, primary key)
- requester_username (text)
- receiver_username (text)
- status (text) - 'pending_verification' or 'verified'

**messages**:
- id (uuid, primary key)
- sender_username (text)
- recipient_username (text)
- ciphertext_b64 (text)
- nonce_b64 (text)
- timestamp_b64 (text)

## Usage

1. **Register/Login**: Create an account or login with Supabase
2. **Find Users**: Browse available users in the "Find Users" tab
3. **Request Connection**: Send a connection request to another user
4. **Accept Connection**: Accept pending connection requests
5. **Start Messaging**: Once connected, send encrypted messages and files

## Security Features

- All messages are encrypted end-to-end using AES-GCM
- Keys are derived from XDH shared secrets + Merkle root + timestamp
- Merkle tree proofs verify user identity before connections
- Zero Trust authentication checks device context
- Files are encrypted before transmission

## Development

The system uses your existing encryption logic:
- `core/crypto_utils.py` - XDH key exchange and AES-GCM encryption
- `core/merkle.py` - Merkle tree for identity verification
- `core/blockchain.py` - Blockchain ledger for root storage
- `network/server.py` - ZTA server logic
- `network/client.py` - Secure client implementation

## License

MIT
