# Setup Guide

## Quick Start

### 1. Backend Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Make sure .env file exists with Supabase credentials
# SUPABASE_URL=your_url
# SUPABASE_KEY=your_key

# Start backend server
cd backend
python app.py
```

Backend runs on: http://localhost:5000

### 2. Frontend Setup

```bash
# Install Node dependencies
cd frontend
npm install

# Start development server
npm run dev
```

Frontend runs on: http://localhost:3000

## Supabase Database Setup

Make sure your Supabase project has these tables:

### Table: users
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  username TEXT UNIQUE NOT NULL,
  public_key_hex TEXT NOT NULL,
  merkle_leaf_hash TEXT NOT NULL,
  trust_score INTEGER DEFAULT 100,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Table: connections
```sql
CREATE TABLE connections (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  requester_username TEXT NOT NULL,
  receiver_username TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending_verification',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### Table: messages
```sql
CREATE TABLE messages (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  sender_username TEXT NOT NULL,
  recipient_username TEXT NOT NULL,
  ciphertext_b64 TEXT NOT NULL,
  nonce_b64 TEXT NOT NULL,
  timestamp_b64 TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
```

## Environment Variables

### Backend (.env in project root)
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
```

### Frontend (frontend/.env - optional, defaults provided)
```
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

## Troubleshooting

1. **Backend won't start**: Check that .env file exists and has correct Supabase credentials
2. **Frontend can't connect**: Make sure backend is running on port 5000
3. **Authentication fails**: Verify Supabase project is set up correctly
4. **Database errors**: Ensure all tables exist in Supabase with correct schema

## Features

- ✅ User registration and login via Supabase
- ✅ Zero Trust authentication
- ✅ Merkle tree identity verification
- ✅ End-to-end encrypted messaging
- ✅ Secure file transfer
- ✅ Connection handshake protocol
- ✅ Real-time message polling
