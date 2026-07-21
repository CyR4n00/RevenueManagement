import { createClient } from '@supabase/supabase-js';

const url = process.env.REACT_APP_SUPABASE_URL;
const publishableKey = process.env.REACT_APP_SUPABASE_PUBLISHABLE_KEY;

// A publishable key is designed to be included in browser code.  Database
// access remains constrained by Supabase Auth and Row Level Security.
export const supabase = url && publishableKey
  ? createClient(url, publishableKey, { auth: { persistSession: true, autoRefreshToken: true } })
  : null;

export const authIsConfigured = Boolean(supabase);
