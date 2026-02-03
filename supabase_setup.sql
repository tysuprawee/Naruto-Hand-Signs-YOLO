-- Enable UUID extension if not enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Create the Custom Jutsus Table
CREATE TABLE IF NOT EXISTS public.custom_jutsus (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id TEXT NOT NULL,       -- Stores Discord ID or Username
    name TEXT NOT NULL,          -- Name of the Jutsu (e.g., "Thunder Clap")
    sequence JSONB NOT NULL,     -- The hand signs: ["tiger", "snake", ...]
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    
    -- Constraint: Prevent duplicate jutsu names for the same user
    UNIQUE(user_id, name)
);

-- 2. Create an Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_custom_jutsus_user ON public.custom_jutsus(user_id);

-- 3. Enable Row Level Security (RLS)
ALTER TABLE public.custom_jutsus ENABLE ROW LEVEL SECURITY;

-- 4. Policy: Users can Select only their own jutsus (assuming user_id matches auth)
-- Note: Since we are using a Python app, we might be bypassing RLS with a Service Key,
-- but this is good practice if using Authenticated Client.
-- Make sure to update the 'using' clause to match your actual auth implementation.
CREATE POLICY "Users can view own jutsus" 
ON public.custom_jutsus FOR SELECT 
USING (true); -- START WITH PUBLIC READ for prototype ease, lock down later.

CREATE POLICY "Users can insert own jutsus" 
ON public.custom_jutsus FOR INSERT 
WITH CHECK (true);
