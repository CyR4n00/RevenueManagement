import { useEffect, useState } from 'react';
import axios from 'axios';
import './App.css';
import { SettingsPanel } from './SettingsPanel';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

interface CompetitorPrice {
  date: string;
  competitor_id: number;
  competitor_name: string;
  price_today: number;
  difference: number;
  is_fully_booked: boolean;
  source: 'apify' | 'simulation' | 'unknown';
}
interface Alert { id: number; date: string; message: string; type: 'increase' | 'decrease' | 'sold_out'; }
interface Recommendation { date: string; suggested_price: number; suggested_rank: string; reasoning: string; }
interface PmsProfile { id: string; name: string; verified: boolean; description: string; }

function today() { return new Date().toISOString().slice(0, 10); }

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

  const dates = Array.from({ length: 7 }, (_, index) => {
    const date = new Date(`${selectedDate}T00:00:00`);
    date.setDate(date.getDate() + index);
    return date.toISOString().slice(0, 10);
  });

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      const [market, alert, rec, exportProfiles] = await Promise.all([
        axios.get<CompetitorPrice[]>(`${API_BASE}/market_data`, { params: { start_date: selectedDate, days: 7 } }),
        axios.get<Alert[]>(`${API_BASE}/alerts`, { params: { start_date: selectedDate, days: 7 } }),
        axios.get<Recommendation>(`${API_BASE}/recommendation`, { params: { date: selectedDate } }),
        axios.get<PmsProfile[]>(`${API_BASE}/pms/profiles`),
      ]);
      setMarketData(market.data);
      setAlerts(alert.data);
      setRecommendation(rec.data);
      setProfiles(exportProfiles.data);
    } catch {
      setError('データを取得できませんでした。バックエンドの起動状態と連携設定を確認してください。');
    } finally { setLoading(false); }
  };

  useEffect(() => { fetchData(); }, [selectedDate]); // eslint-disable-line react-hooks/exhaustive-deps

  const competitors = Array.from(new Set(marketData.map(item => item.competitor_name)));
  const hasSimulation = marketData.some(item => item.source === 'simulation');
  const downloadCsv = () => window.open(`${API_BASE}/export_csv?start_date=${selectedDate}&days=7&profile=${profile}`, '_blank', 'noopener,noreferrer');

  return <main className="min-h-screen bg-slate-50 p-4 md:p-8 text-slate-800">
    <div className="mx-auto max-w-6xl space-y-6">
      <header className="flex flex-col gap-4 rounded-xl border bg-white p-4 shadow-sm md:flex-row md:items-center md:justify-between">
        <div><h1 className="text-2xl font-bold">Revenue Assistant</h1><p className="text-sm text-slate-500">競合料金・アラート・安全な価格提案</p></div>
        <div className="flex items-center gap-3">
          <input aria-label="開始日" type="date" value={selectedDate} onChange={event => setSelectedDate(event.target.value)} className="rounded border p-2" disabled={loading} />
          <button onClick={() => setShowSettings(!showSettings)} className="rounded border px-3 py-2 text-sm font-semibold hover:bg-slate-50">設定</button>
        </div>
      </header>

      {showSettings && <SettingsPanel apiBase={API_BASE} onClose={() => { setShowSettings(false); fetchData(); }} />}
      {error && <p role="alert" className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p>}
      {hasSimulation && <p className="rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">現在はデモデータです。実運用前にApify APIトークンとOTA別Actorをサーバー環境変数へ設定してください。</p>}

      <section className="grid gap-6 lg:grid-cols-3">
        <article className="rounded-xl bg-gradient-to-br from-indigo-600 to-blue-600 p-5 text-white shadow">
          <p className="text-xs font-bold uppercase tracking-wider text-blue-100">AI価格提案</p>
          {recommendation ? <><p className="mt-4 text-5xl font-extrabold">ランク {recommendation.suggested_rank}</p><p className="mt-2 text-xl">¥{recommendation.suggested_price.toLocaleString()}</p><p className="mt-4 rounded bg-white/15 p-3 text-sm leading-relaxed">{recommendation.reasoning}</p></> : <p className="mt-4">読み込み中…</p>}
          <div className="mt-5 flex gap-2"><select aria-label="CSVプロファイル" value={profile} onChange={event => setProfile(event.target.value)} className="min-w-0 flex-1 rounded p-2 text-sm text-slate-800">{profiles.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select><button onClick={downloadCsv} className="rounded bg-white px-3 py-2 text-sm font-bold text-blue-700">CSV出力</button></div>
        </article>
        <article className="rounded-xl border bg-white p-5 shadow-sm lg:col-span-2"><h2 className="font-bold">市場アラート</h2><div className="mt-4 space-y-2">{alerts.length ? alerts.map(alert => <p key={alert.id} className={`rounded border-l-4 p-3 text-sm ${alert.type === 'increase' ? 'border-red-500 bg-red-50' : alert.type === 'decrease' ? 'border-blue-500 bg-blue-50' : 'border-slate-500 bg-slate-100'}`}>{alert.message}</p>) : <p className="py-8 text-center text-sm text-slate-400">対象期間に大きな変動はありません。</p>}</div></article>
      </section>

      <section className="overflow-x-auto rounded-xl border bg-white shadow-sm"><div className="border-b bg-slate-800 p-4 text-white"><h2 className="font-bold">レベニュータワー</h2><p className="text-xs text-slate-300">前日比：赤＝上昇、青＝下落、グレー＝満室</p></div><table className="w-full min-w-[780px] border-collapse text-sm"><thead><tr><th className="border-b bg-slate-50 p-3 text-left">競合施設</th>{dates.map(date => <th key={date} className="border-b bg-slate-50 p-3 text-center">{date.slice(5).replace('-', '/')}</th>)}</tr></thead><tbody>{competitors.map(competitor => <tr key={competitor}><th className="border-b p-3 text-left">{competitor}</th>{dates.map(date => { const item = marketData.find(data => data.competitor_name === competitor && data.date === date); if (!item) return <td key={date} className="border-b p-3 text-center">—</td>; if (item.is_fully_booked) return <td key={date} className="border-b bg-slate-100 p-3 text-center text-slate-500">満室</td>; const color = item.difference > 0 ? 'bg-red-50 text-red-700' : item.difference < 0 ? 'bg-blue-50 text-blue-700' : ''; return <td key={date} className={`border-b p-3 text-center ${color}`}><strong>¥{item.price_today.toLocaleString()}</strong><br /><small>{item.difference >= 0 ? '+' : ''}{item.difference.toLocaleString()}</small></td>; })}</tr>)}</tbody></table></section>
    </div>
  </main>;
}

export default App;
