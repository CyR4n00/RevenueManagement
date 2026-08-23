import { createClient } from '@supabase/supabase-js';

declare global {
  interface Window {
    __REVENAVI_CONFIG__?: {
      apiUrl?: string;
      supabaseUrl?: string;
      supabasePublishableKey?: string;
      demoMode?: boolean;
    };
  }
}

export const runtimeConfig = window.__REVENAVI_CONFIG__ || {};
const url = runtimeConfig.supabaseUrl || process.env.REACT_APP_SUPABASE_URL;
const publishableKey = runtimeConfig.supabasePublishableKey || process.env.REACT_APP_SUPABASE_PUBLISHABLE_KEY;

// A publishable key is designed to be included in browser code.  Database
// access remains constrained by Supabase Auth and Row Level Security.
export const supabase = url && publishableKey
  ? createClient(url, publishableKey, { auth: { persistSession: true, autoRefreshToken: true } })
  : null;

// Meeting/demo mode intentionally bypasses Auth in both frontend and backend.
// Production deployments must leave this false or unset.
export const authIsConfigured = Boolean(supabase)
  && runtimeConfig.demoMode !== true
  && process.env.REACT_APP_DEMO_MODE !== 'true';
