import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://ubohcsbleomyvkjkaitj.supabase.co'
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVib2hjc2JsZW9teXZramthaXRqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE1MTU5MjQsImV4cCI6MjA4NzA5MTkyNH0.mTrch9eac3Gailj3gBTimHzP-aAX-owySRsZc36WmTw'

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
