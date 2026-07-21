import { useEffect, useState } from 'react';
import type { Session } from '@supabase/supabase-js';
import axios from 'axios';
import './App.css';
import { AuthGate } from './AuthGate';
import { OnboardingGate } from './OnboardingGate';
import { SettingsPanel } from './SettingsPanel';
import { authIsConfigured, supabase } from './supabase';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

interface CompetitorPrice { date: string; competitor_id: string; competitor_name: string; price_today: number; difference: number; is_fully_booked: boolean; source: 'apify' | 'simulation' | 'unknown'; }
interface Alert { id: number; date: string; message: string; type: 'increase' | 'decrease' | 'sold_out'; }
interface Recommendation { date: string; suggested_price: number; suggested_rank: string; reasoning: string; }
interface PmsProfile { id: string; name: string; verified: boolean; description: string; }

function today() { return new Date().toISOString().slice(0, 10); }

function PasswordRecovery({ onDone }: { onDone: () => void }) {
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const save = async () => {
    if (!supabase || password.length < 8) { setError('8文字以上の新しいパスワードを入力してください。'); return; }
    const { error: updateError } = await supabase.auth.updateUser({ password });
    if (updateError) { setError(updateError.message); return; }
    setMessage('パスワードを更新しました。');
    window.setTimeout(onDone, 700);
  };
  return <main className="min-h-screen bg-slate-50 p-4 text-slate-800 md:p-8"><section className="mx-auto mt-10 max-w-md rounded-xl border bg-white p-6 shadow-sm"><h1 className="text-xl font-bold">パスワードを再設定</h1><label className="mt-5 block text-sm font-semibold">新しいパスワード<input type="password" minLength={8} value={password} onChange={event => setPassword(event.target.value)} className="mt-1 w-full rounded border p-2" /></label><button onClick={save} className="mt-5 rounded bg-blue-600 px-4 py-2 font-semibold text-white">保存する</button>{message && <p className="mt-4 text-sm text-emerald-700">{message}</p>}{error && <p className="mt-4 text-sm text-red-700">{error}</p>}</section></main>;
}

function App() {
  const [selectedDate, setSelectedDate] = useState(today());
  const [marketData, setMarketData] = useState<CompetitorPrice[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [profiles, setProfiles] = useState<PmsProfile[]>([]);
  const [profile, setProfile] = useState('generic');
  const [showSettings, setShowSettings] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [session, setSession] = useState<Session | null>(null);
  const [authLoading, setAuthLoading] = useState(authIsConfigured);
  const [dashboardReady, setDashboardReady] = useState(!authIsConfigured);
  const [passwordRecovery, setPasswordRecovery] = useState(false);

  useEffect(() => {
    if (!supabase) return;
    void supabase.auth.getSession().then(({ data }) => { setSession(data.session); setAuthLoading(false); });
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, nextSession) => {
      setSession(nextSession);
      setAuthLoading(false);
      setDashboardReady(false);
      if (event === 'PASSWORD_RECOVERY') setPasswordRecovery(true);
    });
    return () => subscription.unsubscribe();
  }, []);

  const authHeaders = session ? { Authorization: `Bearer ${session.access_token}` } : {};
  const dates = Array.from({ length: 7 }, (_, index) => { const date = new Date(`${selectedDate}T00:00:00`); date.setDate(date.getDate() + index); return date.toISOString().slice(0, 10); });

  const fetchData = async () => {
    setLoading(true); setError('');
    try {
      // Market data can start a permitted collection when no result exists.
      // Keep dependent requests sequential to avoid duplicate OTA runs on a
      // customer's first dashboard visit.
      const market = await axios.get<CompetitorPrice[]>(`${API_BASE}/market_data`, { params: { start_date: selectedDate, days: 7 }, headers: authHeaders });
      const [alert, rec, exportProfiles] = await Promise.all([
        axios.get<Alert[]>(`${API_BASE}/alerts`, { params: { start_date: selectedDate, days: 7 }, headers: authHeaders }),
        axios.get<Recommendation>(`${API_BASE}/recommendation`, { params: { date: selectedDate }, headers: authHeaders }),
        axios.get<PmsProfile[]>(`${API_BASE}/pms/profiles`, { headers: authHeaders }),
      ]);
      setMarketData(market.data); setAlerts(alert.data); setRecommendation(rec.data); setProfiles(exportProfiles.data);
    } catch (requestError: any) {
      setError(requestError?.response?.status === 401 ? 'ログインの有効期限が切れました。再度ログインしてください。' : 'データを取得できませんでした。接続設定を確認してください。');
    } finally { setLoading(false); }
  };

  useEffect(() => { if (dashboardReady) void fetchData(); }, [selectedDate, dashboardReady, session?.access_token]); // eslint-disable-line react-hooks/exhaustive-deps

  const downloadCsv = async () => {
    try {
      const response = await axios.get(`${API_BASE}/export_csv`, { params: { start_date: selectedDate, days: 7, profile }, headers: authHeaders, responseType: 'blob' });
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement('a'); anchor.href = url; anchor.download = `revenue_${profile}_${selectedDate}.csv`; anchor.click();
      URL.revokeObjectURL(url);
    } catch { setError('CSVを出力できませんでした。'); }
  };
  const signOut = () => { if (supabase) void supabase.auth.signOut(); };

  if (authLoading) return <main className="min-h-screen bg-slate-50 p-8"><p className="mx-auto max-w-md rounded border bg-white p-5 text-sm">ログイン状態を確認しています…</p></main>;
  if (authIsConfigured && !session) return <AuthGate />;
  if (passwordRecovery) return <PasswordRecovery onDone={() => setPasswordRecovery(false)} />;
  if (authIsConfigured && session && !dashboardReady) return <OnboardingGate apiBase={API_BASE} accessToken={session.access_token} onComplete={() => setDashboardReady(true)} />;

  const competitors = Array.from(new Set(marketData.map(item => item.competitor_name)));
  const hasSimulation = marketData.some(item => item.source === 'simulation');
  return <main className="min-h-screen bg-slate-50 p-4 text-slate-800 md:p-8"><div className="mx-auto max-w-6xl space-y-6">
    <header className="flex flex-col gap-4 rounded-xl border bg-white p-4 shadow-sm md:flex-row md:items-center md:justify-between"><div><h1 className="text-2xl font-bold">Revenue Assistant</h1><p className="text-sm text-slate-500">競合価格アラート・安全な価格提案</p></div><div className="flex flex-wrap items-center gap-3">{session && <span className="text-xs text-slate-500">{session.user.email}</span>}<input aria-label="対象日" type="date" value={selectedDate} onChange={event => setSelectedDate(event.target.value)} className="rounded border p-2" disabled={loading} /><button onClick={() => setShowSettings(!showSettings)} className="rounded border px-3 py-2 text-sm font-semibold hover:bg-slate-50">設定</button>{session && <button onClick={signOut} className="rounded border px-3 py-2 text-sm font-semibold hover:bg-slate-50">ログアウト</button>}</div></header>
    {showSettings && <SettingsPanel apiBase={API_BASE} accessToken={session?.access_token || ''} onClose={() => { setShowSettings(false); void fetchData(); }} />}
    {error && <p role="alert" className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p>}
    {hasSimulation && <p className="rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">これはデモ用の疑似データです。本番ではApifyと許諾済みOTAのデータだけを利用します。</p>}
    <section className="grid gap-6 lg:grid-cols-3"><article className="rounded-xl bg-gradient-to-br from-indigo-600 to-blue-600 p-5 text-white shadow"><p className="text-xs font-bold uppercase tracking-wider text-blue-100">AI価格提案</p>{recommendation ? <><p className="mt-4 text-5xl font-extrabold">ランク {recommendation.suggested_rank}</p><p className="mt-2 text-xl">¥{recommendation.suggested_price.toLocaleString()}</p><p className="mt-4 rounded bg-white/15 p-3 text-sm leading-relaxed">{recommendation.reasoning}</p></> : <p className="mt-4">読み込み中…</p>}<div className="mt-5 flex gap-2"><select aria-label="CSVプロファイル" value={profile} onChange={event => setProfile(event.target.value)} className="min-w-0 flex-1 rounded p-2 text-sm text-slate-800">{profiles.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select><button onClick={() => void downloadCsv()} className="rounded bg-white px-3 py-2 text-sm font-bold text-blue-700">CSV出力</button></div></article><article className="rounded-xl border bg-white p-5 shadow-sm lg:col-span-2"><h2 className="font-bold">前日アラート</h2><div className="mt-4 space-y-2">{alerts.length ? alerts.map(alert => <p key={alert.id} className={`rounded border-l-4 p-3 text-sm ${alert.type === 'increase' ? 'border-red-500 bg-red-50' : alert.type === 'decrease' ? 'border-blue-500 bg-blue-50' : 'border-slate-500 bg-slate-100'}`}>{alert.message}</p>) : <p className="py-8 text-center text-sm text-slate-400">対象期間に大きな変化はありません。</p>}</div></article></section>
    <section className="overflow-x-auto rounded-xl border bg-white shadow-sm"><div className="border-b bg-slate-800 p-4 text-white"><h2 className="font-bold">レベニュータワー</h2><p className="text-xs text-slate-300">前日比：値上げは赤、値下げは青、満室はグレー</p></div><table className="w-full min-w-[780px] border-collapse text-sm"><thead><tr><th className="border-b bg-slate-50 p-3 text-left">競合施設</th>{dates.map(date => <th key={date} className="border-b bg-slate-50 p-3 text-center">{date.slice(5).replace('-', '/')}</th>)}</tr></thead><tbody>{competitors.map(competitor => <tr key={competitor}><th className="border-b p-3 text-left">{competitor}</th>{dates.map(date => { const item = marketData.find(data => data.competitor_name === competitor && data.date === date); if (!item) return <td key={date} className="border-b p-3 text-center">—</td>; if (item.is_fully_booked) return <td key={date} className="border-b bg-slate-100 p-3 text-center text-slate-500">満室</td>; const color = item.difference > 0 ? 'bg-red-50 text-red-700' : item.difference < 0 ? 'bg-blue-50 text-blue-700' : ''; return <td key={date} className={`border-b p-3 text-center ${color}`}><strong>¥{item.price_today.toLocaleString()}</strong><br /><small>{item.difference >= 0 ? '+' : ''}{item.difference.toLocaleString()}</small></td>; })}</tr>)}</tbody></table></section>
  </div></main>;
}

export default App;
