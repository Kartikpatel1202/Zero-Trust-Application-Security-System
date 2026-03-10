-- =========================================================
-- Supabase Storage RLS Policies for secure_vault bucket
-- Run this in: Supabase Dashboard > SQL Editor > New Query
-- =========================================================

-- Enable RLS on storage.objects (already enabled by default, but just in case)
-- ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

-- --------------------------------------------------------
-- DROP any existing conflicting policies first (safe to run)
-- --------------------------------------------------------
DROP POLICY IF EXISTS "secure_vault_select"  ON storage.objects;
DROP POLICY IF EXISTS "secure_vault_insert"  ON storage.objects;
DROP POLICY IF EXISTS "secure_vault_update"  ON storage.objects;
DROP POLICY IF EXISTS "secure_vault_delete"  ON storage.objects;

-- --------------------------------------------------------
-- POLICY 1: Allow SELECT (list + download files)
-- --------------------------------------------------------
CREATE POLICY "secure_vault_select"
ON storage.objects
FOR SELECT
TO anon, authenticated
USING (bucket_id = 'secure_vault');

-- --------------------------------------------------------
-- POLICY 2: Allow INSERT (upload files)
-- --------------------------------------------------------
CREATE POLICY "secure_vault_insert"
ON storage.objects
FOR INSERT
TO anon, authenticated
WITH CHECK (bucket_id = 'secure_vault');

-- --------------------------------------------------------
-- POLICY 3: Allow UPDATE (needed for x-upsert overwrite)
-- --------------------------------------------------------
CREATE POLICY "secure_vault_update"
ON storage.objects
FOR UPDATE
TO anon, authenticated
USING (bucket_id = 'secure_vault')
WITH CHECK (bucket_id = 'secure_vault');

-- --------------------------------------------------------
-- POLICY 4: Allow DELETE (optional, for future use)
-- --------------------------------------------------------
CREATE POLICY "secure_vault_delete"
ON storage.objects
FOR DELETE
TO anon, authenticated
USING (bucket_id = 'secure_vault');

-- =========================================================
-- After running this, click "Refresh File Lists" in the app
-- and files should appear in the Received / Sent tabs.
-- =========================================================
