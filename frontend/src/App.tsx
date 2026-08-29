import { useEffect, useState } from 'react';
import type { Session } from '@supabase/supabase-js';
import axios from 'axios';
import './App.css';
import { AuthGate, authErrorMessage } from './AuthGate';
import { OnboardingGate } from './OnboardingGate';
import { SettingsPanel } from './SettingsPanel';
import { OperatorPanel } from './OperatorPanel';
import { PublicPages, PublicPageName } from './PublicPages';
import { authIsConfigured, runtimeConfig, supabase } from './supabase';

const API_BASE = runtimeConfig.apiUrl
  || process.env.REACT_APP_API_URL
  || (window.location.hostname === 'localhost' ? 'http://localhost:8000' : window.location.origin);

interface CompetitorPrice { date: string; competitor_id: string; competitor_name: string; price_today: number; difference: number; comparison_available: boolean; comparison_days: number; was_fully_booked?: boolean | null; is_fully_booked: boolean; availability_status: 'available' | 'limited' | 'sold_out' | 'unknown'; remaining_rooms?: number | null; availability_source: 'explicit_count' | 'symbol' | 'inferred' | 'unknown'; source: 'apify' | 'simulation' | 'unknown'; }
interface Alert { id: number; date: string; message: string; type: 'increase' | 'decrease' | 'sold_out'; }
interface Recommendation { date: string; suggested_price: number; suggested_rank: string; reasoning: string; }
interface RegisteredCompetitor { id: string; name: string | null; url: string; }
interface BillingStatus { configured: boolean; subscription_status: string; plan: 'standard' | 'upgrade'; max_horizon_days: number; }
interface IntegrationStatus { email_delivery_configured: boolean; }
interface CollectionStatus { status: 'ready' | 'attention' | 'not_started'; message: string; last_success_at: string | null; last_attempt_at: string | null; successful_runs_7d: number; failed_runs_7d: number; collected_stay_dates: number; competitor_count: number; scheduled_hours: number[]; }

function localDate(value = new Date()) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function addDays(value: string, amount: number) {
  const [year, month, day] = value.split('-').map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  date.setUTCDate(date.getUTCDate() + amount);
  return date.toISOString().slice(0, 10);
}

function today() { return localDate(); }

function dateTimeLabel(value: string | null | undefined) {
  if (!value) return 'まだありません';
  return new Intl.DateTimeFormat('ja-JP', {
    timeZone: 'Asia/Tokyo', month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit',
  }).format(new Date(value));
}

function datesByMonth(dates: string[]) {
  return dates.reduce<Record<string, string[]>>((groups, date) => {
    const month = date.slice(0, 7);
    (groups[month] ||= []).push(date);
    return groups;
  }, {});
}

const weekdayLabels = ['日', '月', '火', '水', '木', '金', '土'];

function weekdayIndex(date: string) {
  const [year, month, day] = date.split('-').map(Number);
  return new Date(Date.UTC(year, month - 1, day)).getUTCDay();
}

function dateLabel(date: string) {
  const weekday = weekdayIndex(date);
  return { short: date.slice(5).replace('-', '/'), weekday, label: `${date.slice(5).replace('-', '/')}（${weekdayLabels[weekday]}）` };
}

function CalendarWeekHeader() {
  return <div className="hidden grid-cols-7 border-b bg-slate-50 text-center text-xs font-semibold lg:grid">{weekdayLabels.map((label, index) => <div key={label} className={`p-2 ${index === 0 ? 'text-red-600' : index === 6 ? 'text-blue-600' : 'text-slate-500'}`}>{label}</div>)}</div>;
}

function availabilityText(item: CompetitorPrice) {
  if (item.availability_status === 'sold_out' || item.is_fully_booked) return '× 部屋なし';
  if (item.availability_status === 'limited') return `△ 残りわずか${item.remaining_rooms !== null && item.remaining_rooms !== undefined ? `（表示最少${item.remaining_rooms}室）` : ''}`;
  if (item.remaining_rooms !== null && item.remaining_rooms !== undefined) return `○ 空室あり（表示最少${item.remaining_rooms}室）`;
  if (item.availability_status === 'available') return '○ 空室あり';
  return '空室状況不明';
}

type SidebarIconName = 'overview' | 'proposal' | 'compare' | 'calendar' | 'operator' | 'settings' | 'logout';

function SidebarIcon({ name }: { name: SidebarIconName }) {
  const paths = {
    overview: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
    proposal: <><path d="M12 3 4.5 7.5 12 12l7.5-4.5L12 3Z" /><path d="m4.5 12 7.5 4.5 7.5-4.5" /><path d="m4.5 16.5 7.5 4.5 7.5-4.5" /></>,
    compare: <><path d="M5 20V10" /><path d="M12 20V4" /><path d="M19 20v-7" /></>,
    calendar: <><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M16 3v4M8 3v4M3 10h18" /></>,
    operator: <><path d="M12 3 4 6.5v5.2c0 4.6 3.2 7.8 8 9.3 4.8-1.5 8-4.7 8-9.3V6.5L12 3Z" /><path d="M8.5 12.5 11 15l4.8-5" /></>,
    settings: <><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.83 2.83-.06-.06A1.7 1.7 0 0 0 15 19.4a1.7 1.7 0 0 0-1 .6 1.7 1.7 0 0 0-.4 1.1V21h-4v-.1A1.7 1.7 0 0 0 8.6 19.4a1.7 1.7 0 0 0-1.88.34l-.06.06-2.83-2.83.06-.06A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-.6-1 1.7 1.7 0 0 0-1.1-.4H3v-4h.1A1.7 1.7 0 0 0 4.6 8.6a1.7 1.7 0 0 0-.34-1.88l-.06-.06 2.83-2.83.06.06A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-.6 1.7 1.7 0 0 0 .4-1.1V3h4v.1A1.7 1.7 0 0 0 15.4 4.6a1.7 1.7 0 0 0 1.88-.34l.06-.06 2.83 2.83-.06.06A1.7 1.7 0 0 0 19.4 9c.13.38.34.72.6 1 .3.28.68.42 1.1.4h.1v4h-.1c-.42-.02-.8.12-1.1.4-.26.28-.47.62-.6 1Z" /></>,
    logout: <><path d="M10 17l5-5-5-5" /><path d="M15 12H3" /><path d="M15 4h4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-4" /></>,
  };
  return <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>;
}

function DashboardSidebar({ onSettings, onOperator, onSignOut, signedIn, operatorAvailable }: { onSettings: () => void; onOperator: () => void; onSignOut: () => void; signedIn: boolean; operatorAvailable: boolean }) {
  const [activeHash, setActiveHash] = useState(window.location.hash || '#overview');
  useEffect(() => {
    const syncHash = () => setActiveHash(window.location.hash || '#overview');
    window.addEventListener('hashchange', syncHash);
    return () => window.removeEventListener('hashchange', syncHash);
  }, []);
  const items = [
    { href: '#overview', icon: 'overview' as const, label: '概要' },
    { href: '#proposal', icon: 'proposal' as const, label: '参考価格' },
    { href: '#tower', icon: 'compare' as const, label: '価格比較' },
    { href: '#calendar', icon: 'calendar' as const, label: 'カレンダー' },
  ];
  return <aside className="dashboard-sidebar">
    <div className="sidebar-brand" aria-label="レベナビ"><img className="sidebar-logo" src="/revenavi-icon-48.png" alt="" aria-hidden="true" /><span className="sidebar-brand-copy"><strong>レベナビ</strong><small>価格判断支援</small></span></div>
    <nav className="sidebar-nav">{items.map(item => <a key={item.href} href={item.href} onClick={() => setActiveHash(item.href)} title={item.label} aria-label={item.label} aria-current={activeHash === item.href ? 'page' : undefined} className={`sidebar-link ${activeHash === item.href ? 'sidebar-link-active' : ''}`}><span className="sidebar-icon"><SidebarIcon name={item.icon} /></span><span className="sidebar-label">{item.label}</span></a>)}</nav>
    <div className="sidebar-actions"><p className="sidebar-section-label">アカウント</p>{operatorAvailable && <button type="button" onClick={onOperator} title="運営管理" aria-label="運営管理" className="sidebar-link"><span className="sidebar-icon"><SidebarIcon name="operator" /></span><span className="sidebar-label">運営管理</span></button>}<button type="button" onClick={onSettings} title="設定" aria-label="設定" className="sidebar-link"><span className="sidebar-icon"><SidebarIcon name="settings" /></span><span className="sidebar-label">設定</span></button>{signedIn && <button type="button" onClick={onSignOut} title="ログアウト" aria-label="ログアウト" className="sidebar-link sidebar-signout"><span className="sidebar-icon"><SidebarIcon name="logout" /></span><span className="sidebar-label">ログアウト</span></button>}</div>
  </aside>;
}

function RankCalendar({ dates, recommendations, prices, comparisonDays, selectedDate, onSelect }: { dates: string[]; recommendations: Recommendation[]; prices: CompetitorPrice[]; comparisonDays: 1 | 7 | 30; selectedDate: string; onSelect: (date: string) => void }) {
  const monthGroups = datesByMonth(dates);
  const comparisonLabel = comparisonDays === 1 ? '前日比' : comparisonDays === 7 ? '先週比' : '先月比';
  const periodLabel = dates.length === 90 ? '3か月' : dates.length === 180 ? '6か月' : '1年間';
  return <details className="group rounded-xl border bg-white shadow-sm">
    <summary className="flex cursor-pointer list-none items-center justify-between border-b bg-slate-800 p-4 text-white"><div><h2 className="font-bold">{periodLabel}の参考ランクカレンダー</h2><p className="text-xs text-slate-300">日付を押すと、その日の算出根拠を上部に表示します。背景色は競合単価の{comparisonLabel}です。</p></div><span aria-hidden="true" className="text-lg transition-transform group-open:rotate-180">▼</span></summary>
    <div className="space-y-4 bg-slate-100 p-3">{Object.entries(monthGroups).map(([month, monthDates], monthIndex) => <details key={month} open={monthIndex === 0} className="overflow-hidden rounded-lg border bg-white">
      <summary className="cursor-pointer bg-slate-700 px-4 py-3 font-bold text-white">{month.replace('-', '年')}月</summary>
      <CalendarWeekHeader />
      <div className="grid grid-cols-2 gap-px bg-slate-200 sm:grid-cols-4 lg:grid-cols-7">
        {Array.from({ length: weekdayIndex(monthDates[0]) }, (_, index) => <div key={`blank-${index}`} className="hidden min-h-32 bg-slate-50 lg:block" />)}
        {monthDates.map(date => {
          const rec = recommendations.find(item => item.date === date);
          const dayMarket = prices.filter(item => item.date === date);
          const comparable = dayMarket.filter(item => item.comparison_available && !item.is_fully_booked && !item.was_fully_booked);
          const averageDifference = comparable.length ? Math.round(comparable.reduce((sum, item) => sum + item.difference, 0) / comparable.length) : null;
          const soldOutCount = dayMarket.filter(item => item.is_fully_booked).length;
          const tone = soldOutCount && soldOutCount === dayMarket.length ? 'bg-slate-200' : averageDifference !== null && averageDifference > 0 ? 'bg-red-50' : averageDifference !== null && averageDifference < 0 ? 'bg-blue-50' : 'bg-white';
          const meta = dateLabel(date);
          return <button type="button" key={date} disabled={!rec} onClick={() => rec && onSelect(date)} className={`min-h-36 p-3 text-left transition ${tone} ${selectedDate === date ? 'relative z-10 ring-2 ring-inset ring-indigo-600' : ''} ${rec ? 'hover:brightness-95' : 'cursor-default'}`}>
            <div className="flex items-center justify-between"><p className={`text-xs font-bold ${meta.weekday === 0 ? 'text-red-600' : meta.weekday === 6 ? 'text-blue-600' : 'text-slate-500'}`}>{meta.label}</p>{averageDifference !== null && <span className={`text-xs font-bold ${averageDifference > 0 ? 'text-red-700' : averageDifference < 0 ? 'text-blue-700' : 'text-slate-500'}`}>{averageDifference > 0 ? '↑' : averageDifference < 0 ? '↓' : '→'} ¥{Math.abs(averageDifference).toLocaleString()}</span>}</div>
            {rec ? <><p className="mt-2 text-2xl font-extrabold text-indigo-700">ランク {rec.suggested_rank}</p><p className="font-bold">¥{rec.suggested_price.toLocaleString()}</p></> : <p className="mt-3 text-sm text-slate-400">未取得</p>}
            <div className="mt-3 space-y-1">{dayMarket.map(item => <p key={item.competitor_id} className="truncate text-xs text-slate-600" title={`${item.competitor_name} ${availabilityText(item)}`}>{item.competitor_name}: {item.is_fully_booked ? '× 部屋なし' : `¥${item.price_today.toLocaleString()}・${availabilityText(item)}`}</p>)}</div>
          </button>;
        })}
      </div>
    </details>)}</div>
    <div className="flex flex-wrap gap-4 border-t bg-white p-3 text-xs text-slate-600"><span><i className="mr-1 inline-block h-3 w-3 rounded-sm bg-red-100" />競合単価が上昇</span><span><i className="mr-1 inline-block h-3 w-3 rounded-sm bg-blue-100" />競合単価が低下</span><span><i className="mr-1 inline-block h-3 w-3 rounded-sm bg-slate-300" />全競合が部屋なし</span></div>
  </details>;
}

function PasswordRecovery({ onDone }: { onDone: () => void }) {
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const save = async () => {
    if (!supabase || password.length < 8) { setError('8文字以上の新しいパスワードを入力してください。'); return; }
    const { error: updateError } = await supabase.auth.updateUser({ password });
    if (updateError) { setError(authErrorMessage(updateError.message)); return; }
    setMessage('パスワードを更新しました。');
    window.setTimeout(onDone, 700);
  };
  return <main className="min-h-screen bg-slate-50 p-4 text-slate-800 md:p-8"><section className="mx-auto mt-10 max-w-md rounded-xl border bg-white p-6 shadow-sm"><h1 className="text-xl font-bold">パスワードを再設定</h1><label className="mt-5 block text-sm font-semibold">新しいパスワード<input type="password" minLength={8} value={password} onChange={event => setPassword(event.target.value)} className="mt-1 w-full rounded border p-2" /></label><button onClick={save} className="mt-5 rounded bg-blue-600 px-4 py-2 font-semibold text-white">保存する</button>{message && <p className="mt-4 text-sm text-emerald-700">{message}</p>}{error && <p className="mt-4 text-sm text-red-700">{error}</p>}</section></main>;
}

function CompetitorCalendar({ competitor, dates, prices }: { competitor: RegisteredCompetitor; dates: string[]; prices: CompetitorPrice[] }) {
  const rows = prices.filter(item => item.competitor_id === competitor.id);
  const observedDays = rows.length;
  const soldOutDays = rows.filter(item => item.is_fully_booked).length;
  const limitedDays = rows.filter(item => item.availability_status === 'limited').length;
  const availableDays = observedDays - soldOutDays;
  const soldOutRate = observedDays ? (soldOutDays / observedDays) * 100 : 0;
  const coverageRate = dates.length ? (observedDays / dates.length) * 100 : 0;
  const comparisonLabels: Record<number, string> = { 1: '前日比', 7: '先週比', 30: '先月比' };
  const comparisonLabel = comparisonLabels[rows[0]?.comparison_days || 1] || '比較';
  const monthGroups = datesByMonth(dates);
  return <details className="group rounded-xl border bg-white shadow-sm">
    <summary className="flex cursor-pointer list-none flex-col gap-3 border-b p-4 md:flex-row md:items-center md:justify-between">
      <div><h2 className="font-bold">{competitor.name || '比較する宿'}</h2><p className="text-xs text-slate-500">{dates.length}日間の予約サイト掲載価格・部屋なしシグナル・{comparisonLabel}</p></div>
      <div className="flex items-center gap-3"><div className="grid grid-cols-2 gap-2 text-center text-xs lg:grid-cols-4"><div className="rounded bg-slate-100 px-3 py-2"><strong className="block text-base">{observedDays}/{dates.length}日</strong>取得率 {coverageRate.toFixed(1)}%</div><div className="rounded bg-emerald-50 px-3 py-2 text-emerald-800"><strong className="block text-base">{availableDays}</strong>価格あり</div><div className="rounded bg-amber-50 px-3 py-2 text-amber-800"><strong className="block text-base">{limitedDays}</strong>残りわずか</div><div className="rounded bg-slate-800 px-3 py-2 text-white"><strong className="block text-base">{soldOutDays}日 / {soldOutRate.toFixed(1)}%</strong>部屋なし日率</div></div><span aria-hidden="true" className="text-lg text-slate-500 transition-transform group-open:rotate-180">▼</span></div>
    </summary>
    <div className="space-y-3 bg-slate-100 p-3">{Object.entries(monthGroups).map(([month, monthDates], monthIndex) => <details key={month} open={monthIndex === 0} className="overflow-hidden rounded-lg border bg-white">
      <summary className="cursor-pointer bg-slate-800 px-4 py-3 font-bold text-white">{month.replace('-', '年')}月</summary>
      <CalendarWeekHeader />
      <div className="grid grid-cols-2 gap-px bg-slate-200 sm:grid-cols-4 lg:grid-cols-7">{Array.from({ length: weekdayIndex(monthDates[0]) }, (_, index) => <div key={`blank-${index}`} className="hidden min-h-24 bg-slate-50 lg:block" />)}{monthDates.map(date => {
      const item = rows.find(row => row.date === date);
      let comparison = <p className="mt-1 text-xs text-slate-400">比較履歴なし</p>;
      if (item?.comparison_available) {
        if (item.is_fully_booked && item.was_fully_booked === false) comparison = <p className="mt-1 text-xs font-bold text-slate-700">空室あり → 部屋なし</p>;
        else if (!item.is_fully_booked && item.was_fully_booked) comparison = <p className="mt-1 text-xs font-bold text-emerald-700">部屋なし → 空室あり</p>;
        else if (item.is_fully_booked) comparison = <p className="mt-1 text-xs text-slate-600">継続して部屋なし</p>;
        else comparison = <p className={`mt-1 text-xs ${item.difference > 0 ? 'text-red-600' : item.difference < 0 ? 'text-blue-600' : 'text-slate-400'}`}>{item.difference > 0 ? '↑' : item.difference < 0 ? '↓' : '→'} {item.difference >= 0 ? '+' : ''}¥{item.difference.toLocaleString()}</p>;
      }
      const meta = dateLabel(date);
      const tone = item?.is_fully_booked ? 'bg-slate-200' : item?.availability_status === 'limited' ? 'bg-amber-50' : item?.comparison_available && item.difference > 0 ? 'bg-red-50' : item?.comparison_available && item.difference < 0 ? 'bg-blue-50' : 'bg-white';
      return <article key={date} className={`min-h-24 p-3 ${tone}`}><p className={`text-xs font-bold ${meta.weekday === 0 ? 'text-red-600' : meta.weekday === 6 ? 'text-blue-600' : 'text-slate-500'}`}>{meta.label}</p>{!item ? <p className="mt-3 text-sm text-slate-400">未取得</p> : <>{item.is_fully_booked ? <p className="mt-3 font-bold text-slate-700">× 部屋なし</p> : <><p className="mt-3 text-lg font-extrabold text-indigo-700">¥{item.price_today.toLocaleString()}</p><p className={`mt-1 text-xs font-semibold ${item.availability_status === 'limited' ? 'text-amber-700' : 'text-emerald-700'}`}>{availabilityText(item)}</p></>}{comparison}</>}</article>;
      })}</div>
    </details>)}</div>
    <p className="border-t bg-amber-50 p-3 text-xs text-amber-900">部屋なし日率は、取得済み日数のうち、この予約サイトが「満室・空室なし」を返した割合です。施設全体の実稼働率や残室数ではなく、掲載先ごとの需要の目安として利用します。</p>
  </details>;
}

function App() {
  const [selectedDate, setSelectedDate] = useState(today());
  const [focusedDate, setFocusedDate] = useState(today());
  const [marketData, setMarketData] = useState<CompetitorPrice[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [registeredCompetitors, setRegisteredCompetitors] = useState<RegisteredCompetitor[]>([]);
  const [showSettings, setShowSettings] = useState(false);
  const [showOperator, setShowOperator] = useState(false);
  const [operatorAvailable, setOperatorAvailable] = useState(false);
  const [operatorChecked, setOperatorChecked] = useState(!authIsConfigured);
  const [currentHash, setCurrentHash] = useState(window.location.hash);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [warning, setWarning] = useState('');
  const [session, setSession] = useState<Session | null>(null);
  const [authLoading, setAuthLoading] = useState(authIsConfigured);
  const [dashboardReady, setDashboardReady] = useState(!authIsConfigured);
  const [passwordRecovery, setPasswordRecovery] = useState(false);
  const [comparisonDays, setComparisonDays] = useState<1 | 7 | 30>(1);
  const [horizonDays, setHorizonDays] = useState<90 | 180 | 365>(90);
  const [billingStatus, setBillingStatus] = useState<BillingStatus | null>(null);
  const [integrationStatus, setIntegrationStatus] = useState<IntegrationStatus | null>(null);
  const [collectionStatus, setCollectionStatus] = useState<CollectionStatus | null>(null);

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

  useEffect(() => {
    const updateHash = () => setCurrentHash(window.location.hash);
    window.addEventListener('hashchange', updateHash);
    return () => window.removeEventListener('hashchange', updateHash);
  }, []);

  const authHeaders = session ? { Authorization: `Bearer ${session.access_token}` } : {};
  const dates = Array.from({ length: 7 }, (_, index) => addDays(selectedDate, index));
  const horizonDates = Array.from({ length: horizonDays }, (_, index) => addDays(selectedDate, index));

  const fetchData = async () => {
    setLoading(true); setError(''); setWarning('');
    try {
      // Opening or refreshing the dashboard must never consume an Apify run.
      // Collection is owned by Cloud Scheduler; customers only read cached rows.
      const [market, alert, recs, competitorData, billing, integration, collection] = await Promise.all([
        axios.get<CompetitorPrice[]>(`${API_BASE}/market_data/cached`, { params: { start_date: selectedDate, days: horizonDays, comparison_days: comparisonDays }, headers: authHeaders }),
        axios.get<Alert[]>(`${API_BASE}/alerts`, { params: { start_date: selectedDate, days: 7, comparison_days: comparisonDays }, headers: authHeaders }),
        axios.get<Recommendation[]>(`${API_BASE}/recommendations`, { params: { start_date: selectedDate, days: horizonDays, comparison_days: comparisonDays }, headers: authHeaders }),
        axios.get<RegisteredCompetitor[]>(`${API_BASE}/competitors`, { headers: authHeaders }),
        axios.get<BillingStatus>(`${API_BASE}/billing/status`, { headers: authHeaders }),
        axios.get<IntegrationStatus>(`${API_BASE}/integrations/status`, { headers: authHeaders }),
        axios.get<CollectionStatus>(`${API_BASE}/collection/status`, { headers: authHeaders }),
      ]);
      const recommendationRows = Array.isArray(recs.data) ? recs.data : [];
      setMarketData(market.data); setAlerts(alert.data); setRecommendations(recommendationRows); setRecommendation(recommendationRows[0] || null); setRegisteredCompetitors(competitorData.data); setBillingStatus(billing.data);
      setIntegrationStatus(integration.data); setCollectionStatus(collection.data);
    } catch (requestError: any) {
      setError(requestError?.response?.status === 401 ? 'ログインの有効期限が切れました。再度ログインしてください。' : 'データを取得できませんでした。接続設定を確認してください。');
    } finally { setLoading(false); }
  };

  useEffect(() => { if (dashboardReady) void fetchData(); }, [selectedDate, comparisonDays, horizonDays, dashboardReady, session?.access_token]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!session) { setOperatorAvailable(false); setOperatorChecked(true); return; }
    setOperatorChecked(false);
    void axios.get(`${API_BASE}/operator/summary`, { headers: { Authorization: `Bearer ${session.access_token}` } })
      .then(() => setOperatorAvailable(true))
      .catch(() => setOperatorAvailable(false))
      .finally(() => setOperatorChecked(true));
  }, [session]);
  useEffect(() => { setFocusedDate(selectedDate); }, [selectedDate]);

  const signOut = () => { if (supabase) void supabase.auth.signOut(); };

  const publicPage = currentHash.slice(1) as PublicPageName;
  if (['terms', 'privacy', 'commerce', 'contact'].includes(publicPage)) return <PublicPages apiBase={API_BASE} page={publicPage} />;

  if (authLoading) return <main className="min-h-screen bg-slate-50 p-8"><p className="mx-auto max-w-md rounded border bg-white p-5 text-sm">ログイン状態を確認しています…</p></main>;
  if (authIsConfigured && !session) return <AuthGate />;
  if (passwordRecovery) return <PasswordRecovery onDone={() => setPasswordRecovery(false)} />;
  if (authIsConfigured && session && !dashboardReady && !operatorChecked) return <main className="min-h-screen bg-slate-950 p-8"><p className="mx-auto max-w-md rounded-xl border border-slate-700 bg-slate-900 p-5 text-sm text-white">運営者権限を確認しています…</p></main>;
  if (authIsConfigured && session && !dashboardReady && operatorAvailable) return <main className="min-h-screen bg-slate-950 p-3 md:p-8"><div className="mx-auto max-w-6xl"><OperatorPanel apiBase={API_BASE} accessToken={session.access_token} onClose={signOut} /></div></main>;
  if (authIsConfigured && session && !dashboardReady) return <OnboardingGate apiBase={API_BASE} accessToken={session.access_token} onComplete={() => setDashboardReady(true)} />;

  const competitors = registeredCompetitors.length ? registeredCompetitors.map(item => item.name || '競合施設') : Array.from(new Set(marketData.map(item => item.competitor_name)));
  const hasSimulation = marketData.some(item => item.source === 'simulation');
  const focusedRecommendation = recommendations.find(item => item.date === focusedDate) || recommendation;
  const analysedDates = new Set(marketData.map(item => item.date)).size;
  const movementSignals = marketData.filter(item => item.comparison_available && item.difference !== 0).length;
  const focusedMarket = marketData.filter(item => item.date === focusedDate);
  const availableMarket = focusedMarket.filter(item => !item.is_fully_booked);
  const marketAverage = availableMarket.length ? Math.round(availableMarket.reduce((sum, item) => sum + item.price_today, 0) / availableMarket.length) : null;
  const soldOutCount = focusedMarket.filter(item => item.is_fully_booked).length;
  const averageMovement = availableMarket.filter(item => item.comparison_available).length ? Math.round(availableMarket.filter(item => item.comparison_available).reduce((sum, item) => sum + item.difference, 0) / availableMarket.filter(item => item.comparison_available).length) : null;
  const comparisonReadyCount = marketData.filter(item => item.comparison_available).length;
  return <main className="dashboard-stage min-h-screen p-2 text-slate-900 md:p-6"><div className="dashboard-shell">
    <DashboardSidebar onSettings={() => setShowSettings(true)} onOperator={() => setShowOperator(true)} onSignOut={signOut} signedIn={Boolean(session)} operatorAvailable={operatorAvailable} />
    <div className="dashboard-workspace min-w-0 flex-1">
    <header className="flex flex-col gap-4 border-b border-slate-100 px-5 py-5 md:flex-row md:items-center md:justify-between md:px-8"><div><p className="text-xs font-bold tracking-[0.2em] text-indigo-500">レベナビ</p><h1 className="mt-1 text-3xl font-black tracking-tight">価格分析ダッシュボード</h1><p className="mt-1 text-sm text-slate-500">競合市場を読み解き、今日の販売判断をつくる</p></div><div className="flex flex-wrap items-center gap-3"><label className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs font-semibold text-slate-500 shadow-sm">対象日 <input aria-label="対象日" type="date" value={selectedDate} onChange={event => setSelectedDate(event.target.value)} className="ml-2 bg-transparent font-bold text-slate-900 outline-none" disabled={loading} /></label>{session && <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white py-1 pl-1 pr-3 shadow-sm"><span className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 text-xs font-black text-white">{session.user.email?.slice(0, 1).toUpperCase()}</span><span className="max-w-36 truncate text-xs font-bold">{session.user.email}</span></div>}</div></header>
    <div className="space-y-6 p-4 md:p-8">
    {showSettings && <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-3 backdrop-blur-sm" onMouseDown={event => { if (event.target === event.currentTarget) setShowSettings(false); }}><SettingsPanel apiBase={API_BASE} accessToken={session?.access_token || ''} onClose={() => { setShowSettings(false); void fetchData(); }} /></div>}
    {showOperator && <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-3 backdrop-blur-sm" onMouseDown={event => { if (event.target === event.currentTarget) setShowOperator(false); }}><OperatorPanel apiBase={API_BASE} accessToken={session?.access_token || ''} onClose={() => setShowOperator(false)} /></div>}
    {error && <p role="alert" className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p>}
    {warning && <p role="status" className="rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">{warning}</p>}
    {hasSimulation && <p className="rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">これはデモ用の疑似データです。本番ではApifyと許諾済みOTAのデータだけを利用します。</p>}
    {collectionStatus && <section aria-label="データ更新状況" className={`rounded-xl border p-4 ${collectionStatus.status === 'ready' ? 'border-emerald-200 bg-emerald-50' : 'border-amber-200 bg-amber-50'}`}><div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><div><p className={`text-sm font-bold ${collectionStatus.status === 'ready' ? 'text-emerald-800' : 'text-amber-900'}`}>{collectionStatus.status === 'ready' ? '自動取得は正常です' : collectionStatus.status === 'not_started' ? '初回データを待っています' : '自動取得を確認しています'}</p><p className="mt-1 text-xs text-slate-700">{collectionStatus.message}</p><p className="mt-1 text-xs text-slate-500">最終成功：{dateTimeLabel(collectionStatus.last_success_at)} ／ 直近7日：成功{collectionStatus.successful_runs_7d}回・失敗{collectionStatus.failed_runs_7d}回</p></div><button type="button" onClick={() => void fetchData()} disabled={loading} className="shrink-0 rounded-lg border bg-white px-4 py-2 text-sm font-semibold text-slate-700 disabled:opacity-50">{loading ? '確認中…' : '表示を更新'}</button></div></section>}
    <section id="overview"><div className="mb-4 flex items-center justify-between"><div><h2 className="text-lg font-black">今日の市場スナップショット</h2><p className="text-xs text-slate-500">{dateLabel(focusedDate).label}の競合市場</p></div><span className={`flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-bold ${marketData.length ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-800'}`}><i className="ai-pulse" />{loading ? '表示更新中' : marketData.length ? `実データ ${analysedDates}日` : 'データ未取得'}</span></div><div className="overview-grid">
      <article className="portfolio-card"><div className="flex items-start justify-between"><div><p className="text-xs font-semibold text-slate-500">競合平均価格</p><p className="mt-2 text-3xl font-black">{marketAverage === null ? '—' : `¥${marketAverage.toLocaleString()}`}</p></div><span className={`rounded-full px-3 py-1 text-xs font-bold ${averageMovement !== null && averageMovement > 0 ? 'bg-red-50 text-red-700' : averageMovement !== null && averageMovement < 0 ? 'bg-blue-50 text-blue-700' : 'bg-white/70 text-slate-500'}`}>{averageMovement === null ? '比較履歴なし' : `${averageMovement >= 0 ? '+' : ''}¥${averageMovement.toLocaleString()}`}</span></div><svg viewBox="0 0 420 95" className="mt-6 h-24 w-full" preserveAspectRatio="none" aria-hidden="true"><path d="M0 72 C38 68 55 76 88 61 S145 65 174 48 S231 54 267 37 S326 43 355 25 S395 33 420 12" fill="none" stroke="#7db7db" strokeWidth="3" /><path d="M0 72 C38 68 55 76 88 61 S145 65 174 48 S231 54 267 37 S326 43 355 25 S395 33 420 12 L420 95 L0 95Z" fill="rgba(125,183,219,.13)" /></svg><div className="flex items-center justify-between text-[11px] font-semibold text-slate-400"><span>{registeredCompetitors.length}施設</span><span>{analysedDates}日取得済み</span><span>{movementSignals}変動</span></div></article>
      <article className="asset-card bg-[#e8def4]"><p className="text-xs font-bold text-slate-500">参考ランク</p><p className="mt-4 text-4xl font-black">{focusedRecommendation?.suggested_rank || '—'}</p><p className="mt-2 text-sm font-bold">{focusedRecommendation ? `¥${focusedRecommendation.suggested_price.toLocaleString()}` : '未算出'}</p><span className="mt-auto inline-flex h-10 w-10 items-center justify-center rounded-xl bg-white text-lg">✦</span></article>
      <article className="asset-card bg-[#dcefdc]"><p className="text-xs font-bold text-slate-500">価格変動</p><p className="mt-4 text-2xl font-black">{averageMovement === null ? '—' : `${averageMovement >= 0 ? '↑' : '↓'} ¥${Math.abs(averageMovement).toLocaleString()}`}</p><p className="mt-2 text-xs font-semibold text-emerald-800">{comparisonDays === 1 ? '前日比' : comparisonDays === 7 ? '先週比' : '先月比'}の平均</p><span className="mt-auto inline-flex h-10 w-10 items-center justify-center rounded-xl bg-white text-lg">↗</span></article>
      <article className="asset-card bg-[#f6efd2]"><p className="text-xs font-bold text-slate-500">部屋なしシグナル</p><p className="mt-4 text-3xl font-black">{soldOutCount}<small className="ml-1 text-sm">/{focusedMarket.length}</small></p><p className="mt-2 text-xs font-semibold text-amber-800">予約サイト掲載状況</p><span className="mt-auto inline-flex h-10 w-10 items-center justify-center rounded-xl bg-white text-lg">⌂</span></article>
    </div></section>
    <details id="proposal" open className="group rounded-2xl border border-slate-200 bg-white shadow-sm">
      <summary className="flex cursor-pointer list-none items-center justify-between p-4"><div><h2 className="font-bold">参考価格・アラート</h2><p className="text-xs text-slate-500">競合価格から算出した参考ランクと重要な価格変動</p></div><span aria-hidden="true" className="text-lg text-slate-500 transition-transform group-open:rotate-180">▼</span></summary>
      <section className="grid gap-6 border-t p-4 lg:grid-cols-3"><article id="focused-proposal" className="ai-proposal relative overflow-hidden rounded-2xl border border-cyan-300/20 bg-gradient-to-br from-slate-950 via-indigo-950 to-violet-900 p-5 text-white shadow-xl"><div className="ai-scan" /><div className="relative"><div className="flex items-center justify-between gap-3"><p className="text-xs font-bold tracking-[0.18em] text-cyan-300">市場参考値</p><span className="flex items-center gap-1 rounded-full bg-emerald-400/15 px-2 py-1 text-[10px] font-bold text-emerald-300"><i className="ai-pulse" />ルール計算完了</span></div><p className="mt-1 text-xs text-indigo-200">対象日 · {dateLabel(focusedDate).label}</p>{focusedRecommendation ? <><div className="mt-5 flex items-end gap-3"><p className="text-6xl font-black leading-none">{focusedRecommendation.suggested_rank}</p><div><p className="text-xs text-indigo-200">参考ランク</p><p className="text-xl font-bold">¥{focusedRecommendation.suggested_price.toLocaleString()}</p></div></div><div className="mt-5 rounded-xl border border-white/10 bg-white/10 p-4 backdrop-blur"><p className="text-xs font-bold text-cyan-200">算出根拠</p><p className="mt-2 text-sm leading-relaxed text-indigo-50">{focusedRecommendation.reasoning}</p></div><p className="mt-3 text-[11px] leading-relaxed text-indigo-200">競合状況を基にした参考値です。販売価格を自動変更するものではありません。</p></> : <p className="mt-5">この日付のデータは未取得です。</p>}</div></article><article className="rounded-xl border bg-white p-5 shadow-sm lg:col-span-2"><div className="flex items-center justify-between"><h2 className="font-bold">価格変動アラート</h2><span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">{integrationStatus?.email_delivery_configured ? '画面＋メール通知' : '画面内通知'}</span></div><div className="mt-4 space-y-2">{alerts.length ? alerts.map(alert => <p key={alert.id} className={`rounded border-l-4 p-3 text-sm ${alert.type === 'increase' ? 'border-red-500 bg-red-50' : alert.type === 'decrease' ? 'border-blue-500 bg-blue-50' : 'border-slate-500 bg-slate-100'}`}>{alert.message}</p>) : <p className="py-8 text-center text-sm text-slate-400">対象期間に大きな変化はありません。</p>}</div><p className="mt-4 border-t pt-3 text-xs text-slate-500">{integrationStatus?.email_delivery_configured ? '重要な変化は、登録済みのログインメールにも送信されます。' : 'メール配信は準備中です。現在はこのダッシュボード内に表示されます。'}</p></article></section>
    </details>
    <details id="tower" open className="group overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"><summary className="flex cursor-pointer list-none items-center justify-between border-b p-5"><div><h2 className="font-black">レベニュータワー</h2><p className="text-xs text-slate-500">{comparisonDays === 1 ? '前日比' : comparisonDays === 7 ? '先週比' : '先月比'}：値上げは赤、値下げは青、満室はグレー</p></div><span aria-hidden="true" className="text-lg transition-transform group-open:rotate-180">▼</span></summary><div className="overflow-x-auto"><table className="w-full min-w-[780px] border-collapse text-sm"><thead><tr><th className="sticky left-0 z-20 min-w-44 border-b border-r bg-slate-50 p-3 text-left shadow-[4px_0_8px_-6px_rgba(15,23,42,.45)]">競合施設</th>{dates.map(date => <th key={date} className="min-w-24 border-b bg-slate-50 p-3 text-center">{date.slice(5).replace('-', '/')}</th>)}</tr></thead><tbody>{competitors.map(competitor => <tr key={competitor}><th className="sticky left-0 z-10 min-w-44 border-b border-r bg-white p-3 text-left shadow-[4px_0_8px_-6px_rgba(15,23,42,.45)]">{competitor}</th>{dates.map(date => { const item = marketData.find(data => data.competitor_name === competitor && data.date === date); if (!item) return <td key={date} className="border-b p-3 text-center">—</td>; if (item.is_fully_booked) return <td key={date} className="border-b bg-slate-100 p-3 text-center text-slate-500">満室</td>; const color = item.difference > 0 ? 'bg-red-50 text-red-700' : item.difference < 0 ? 'bg-blue-50 text-blue-700' : ''; return <td key={date} className={`border-b p-3 text-center ${color}`}><strong>¥{item.price_today.toLocaleString()}</strong><br /><small>{item.comparison_available ? `${item.difference >= 0 ? '+' : ''}${item.difference.toLocaleString()}` : '履歴なし'}</small></td>; })}</tr>)}</tbody></table></div></details>
    <details open className="group rounded-xl border bg-white shadow-sm"><summary className="flex cursor-pointer list-none items-center justify-between p-4"><div><h2 className="font-bold">表示期間</h2><p className="text-xs text-slate-500">通常プランは最大6か月、アップグレードプランは最大1年間です。</p></div><span aria-hidden="true" className="text-lg text-slate-500 transition-transform group-open:rotate-180">▼</span></summary><div className="flex flex-wrap gap-2 border-t p-4">{([90, 180, 365] as const).map(days => { const locked = days > (billingStatus?.max_horizon_days || 180); return <button key={days} type="button" onClick={() => !locked && setHorizonDays(days)} disabled={loading || locked} title={locked ? 'アップグレードプランで利用できます' : undefined} className={`rounded-lg border px-4 py-2 text-sm font-semibold ${horizonDays === days ? 'border-blue-600 bg-blue-600 text-white' : locked ? 'cursor-not-allowed bg-slate-100 text-slate-400' : 'bg-white text-slate-700 hover:bg-slate-50'}`}>{days === 90 ? '3か月' : days === 180 ? '6か月' : '1年（アップグレード）'}</button>; })}</div></details>
    <div id="calendar"><RankCalendar dates={horizonDates} recommendations={recommendations} prices={marketData} comparisonDays={comparisonDays} selectedDate={focusedDate} onSelect={date => { setFocusedDate(date); setRecommendation(recommendations.find(item => item.date === date) || null); document.getElementById('focused-proposal')?.scrollIntoView({ behavior: 'smooth', block: 'center' }); }} /></div>
    <details open className="group rounded-xl border bg-white shadow-sm"><summary className="flex cursor-pointer list-none items-center justify-between p-4"><div><h2 className="font-bold">価格変動の比較基準</h2><p className="text-xs text-slate-500">同じ宿泊日の現在価格を、過去の取得時点と比較します。</p></div><span aria-hidden="true" className="text-lg text-slate-500 transition-transform group-open:rotate-180">▼</span></summary><div className="border-t p-4"><div className="flex flex-wrap items-center gap-3"><div className="flex rounded-lg bg-slate-100 p-1">{([1, 7, 30] as const).map(days => <button key={days} type="button" onClick={() => setComparisonDays(days)} disabled={loading} className={`rounded-md px-4 py-2 text-sm font-semibold ${comparisonDays === days ? 'bg-white text-blue-700 shadow-sm' : 'text-slate-600'}`}>{days === 1 ? '前日比' : days === 7 ? '先週比' : '先月比'}</button>)}</div><span className={`rounded-full px-3 py-1.5 text-xs font-bold ${comparisonReadyCount ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-800'}`}>比較可能 {comparisonReadyCount}/{marketData.length}件</span></div>{!comparisonReadyCount && <p className="mt-3 text-xs text-amber-800">選択した期間の過去取得履歴がありません。毎日取得すると、前日比は翌日、先週比は7日後、先月比は30日後から表示されます。</p>}</div></details>
    {registeredCompetitors.map(competitor => <CompetitorCalendar key={competitor.id} competitor={competitor} dates={horizonDates} prices={marketData} />)}
    </div></div>
  </div></main>;
}

export default App;
