import { FormEvent, useEffect, useState } from 'react';
import axios from 'axios';

interface Facility { id: string; name: string; address?: string; base_price: number; min_price: number; max_price: number; }
interface OnboardingStatus { subscription_status: string; onboarding_complete: boolean; facility?: Facility | null; }
interface CompetitorDraft { name: string; url: string; }

const initialCompetitor = (): CompetitorDraft => ({ name: '', url: '' });

export function OnboardingGate({ apiBase, accessToken, onComplete }: { apiBase: string; accessToken: string; onComplete: () => void }) {
  const [status, setStatus] = useState<OnboardingStatus | null>(null);
  const [facilityName, setFacilityName] = useState('');
  const [address, setAddress] = useState('');
  const [basePrice, setBasePrice] = useState(10000);
  const [minPrice, setMinPrice] = useState(5000);
  const [maxPrice, setMaxPrice] = useState(30000);
  const [competitors, setCompetitors] = useState<CompetitorDraft[]>([initialCompetitor()]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const headers = { Authorization: `Bearer ${accessToken}` };

  const load = async () => {
    try {
      const response = await axios.get<OnboardingStatus>(`${apiBase}/onboarding/status`, { headers });
      setStatus(response.data);
      if (response.data.onboarding_complete) onComplete();
    } catch {
      setError('初期設定の状態を読み込めませんでした。ログインし直してから再度お試しください。');
    }
  };

  useEffect(() => { void load(); }, [accessToken]); // eslint-disable-line react-hooks/exhaustive-deps

  const startCheckout = async () => {
    setBusy(true); setError('');
    try {
      const response = await axios.post<{ checkout_url: string }>(`${apiBase}/billing/checkout`, {}, { headers });
      window.location.assign(response.data.checkout_url);
    } catch (requestError: any) {
      setError(requestError?.response?.status === 503 ? '現在は決済の準備中です。運営者へお問い合わせください。' : '決済画面を開けませんでした。');
    } finally { setBusy(false); }
  };

  const submitSetup = async (event: FormEvent) => {
    event.preventDefault();
    const completedCompetitors = competitors.filter(item => item.name.trim() || item.url.trim());
    if (minPrice > maxPrice) { setError('最低価格は最高価格以下にしてください。'); return; }
    if (!completedCompetitors.length || completedCompetitors.some(item => !item.name.trim() || !item.url.trim())) {
      setError('比較する競合施設の名称とOTA URLを、少なくとも1件入力してください。'); return;
    }
    setBusy(true); setError('');
    try {
      await axios.post(`${apiBase}/onboarding`, {
        facility_name: facilityName, address, base_price: basePrice, min_price: minPrice, max_price: maxPrice,
        competitors: completedCompetitors,
      }, { headers });
      onComplete();
    } catch (requestError: any) {
      setError(requestError?.response?.data?.detail || '保存できませんでした。URLと価格設定を確認してください。');
    } finally { setBusy(false); }
  };

  if (!status) return <main className="min-h-screen bg-slate-50 p-8"><p className="mx-auto max-w-md rounded border bg-white p-5 text-sm">初期設定を確認しています…</p>{error && <p className="mx-auto mt-3 max-w-md text-sm text-red-700">{error}</p>}</main>;

  const paymentActive = status.subscription_status === 'active';
  return <main className="min-h-screen bg-slate-50 p-4 text-slate-800 md:p-8"><section className="mx-auto max-w-2xl rounded-xl border bg-white p-6 shadow-sm"><h1 className="text-2xl font-bold">利用開始設定</h1>
    {!paymentActive ? <div className="mt-5 space-y-4"><p className="rounded bg-blue-50 p-4 text-sm text-blue-900">月額プランに登録後、施設情報と競合URLを入力するとすぐに利用を開始できます。無料トライアルはありません。</p><button onClick={startCheckout} disabled={busy} className="rounded bg-blue-600 px-5 py-2 font-semibold text-white disabled:opacity-50">月額プランを開始する</button>{new URLSearchParams(window.location.search).get('checkout') === 'success' && <p className="text-sm text-amber-800">決済を確認しています。数秒後にこのページを再読み込みしてください。</p>}</div> : <form className="mt-5 space-y-5" onSubmit={submitSetup}>
      <p className="rounded bg-emerald-50 p-3 text-sm text-emerald-900">決済を確認しました。以下を入力すると利用を開始できます。</p>
      <div className="grid gap-4 md:grid-cols-2"><label className="text-sm font-semibold">施設名<input required value={facilityName} onChange={event => setFacilityName(event.target.value)} className="mt-1 w-full rounded border p-2" /></label><label className="text-sm font-semibold">住所<input required value={address} onChange={event => setAddress(event.target.value)} className="mt-1 w-full rounded border p-2" /></label></div>
      <div><h2 className="font-semibold">価格ガードレール</h2><p className="mt-1 text-xs text-slate-500">AIの提案は必ずこの範囲内に収まります。</p><div className="mt-3 grid gap-3 md:grid-cols-3"><label className="text-sm">基準価格<input required type="number" min="0" value={basePrice} onChange={event => setBasePrice(Number(event.target.value))} className="mt-1 w-full rounded border p-2" /></label><label className="text-sm">最低価格<input required type="number" min="0" value={minPrice} onChange={event => setMinPrice(Number(event.target.value))} className="mt-1 w-full rounded border p-2" /></label><label className="text-sm">最高価格<input required type="number" min="0" value={maxPrice} onChange={event => setMaxPrice(Number(event.target.value))} className="mt-1 w-full rounded border p-2" /></label></div></div>
      <div><h2 className="font-semibold">競合施設</h2><p className="mt-1 text-xs text-slate-500">じゃらん・楽天トラベル・Booking.com等の施設URLを、最大3件貼り付けてください。許諾待ちのOTAはURLだけ保存され、取得は実行されません。</p><div className="mt-3 space-y-3">{competitors.map((competitor, index) => <div key={index} className="grid gap-2 rounded border bg-slate-50 p-3 md:grid-cols-[1fr_2fr_auto]"><input required placeholder="競合施設名" value={competitor.name} onChange={event => setCompetitors(items => items.map((item, itemIndex) => itemIndex === index ? { ...item, name: event.target.value } : item))} className="rounded border p-2 text-sm" /><input required type="url" placeholder="https://..." value={competitor.url} onChange={event => setCompetitors(items => items.map((item, itemIndex) => itemIndex === index ? { ...item, url: event.target.value } : item))} className="rounded border p-2 text-sm" />{competitors.length > 1 && <button type="button" onClick={() => setCompetitors(items => items.filter((_, itemIndex) => itemIndex !== index))} className="rounded border px-3 text-sm">削除</button>}</div>)}</div>{competitors.length < 3 && <button type="button" onClick={() => setCompetitors(items => [...items, initialCompetitor()])} className="mt-3 text-sm font-semibold text-blue-700 hover:underline">＋ 競合を追加</button>}</div>
      {error && <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-800">{error}</p>}
      <button disabled={busy} className="rounded bg-blue-600 px-5 py-2 font-semibold text-white disabled:opacity-50">設定を保存してダッシュボードへ</button>
    </form>}
    {error && !paymentActive && <p role="alert" className="mt-4 rounded bg-red-50 p-3 text-sm text-red-800">{error}</p>}
  </section></main>;
}
