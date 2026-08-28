import { FormEvent, useEffect, useState } from 'react';
import axios from 'axios';
import { userFacingErrorMessage } from './errorMessages';
import { checkOtaPropertyUrl, OtaUrlHelp } from './OtaUrlHelp';

interface Facility { id: string; name: string; address?: string; base_price: number; min_price: number; max_price: number; }
interface OnboardingStatus { subscription_status: string; onboarding_complete: boolean; facility?: Facility | null; }
interface CompetitorDraft { name: string; url: string; }
interface RateRankDraft { label: string; price_jpy: number; }

const initialCompetitor = (): CompetitorDraft => ({ name: '', url: '' });
const initialRateRanks = (): RateRankDraft[] => [
  { label: 'A', price_jpy: 30000 },
  { label: 'B', price_jpy: 20000 },
  { label: 'C', price_jpy: 10000 },
  { label: 'D', price_jpy: 5000 },
];

export function OnboardingGate({ apiBase, accessToken, onComplete }: { apiBase: string; accessToken: string; onComplete: () => void }) {
  const [status, setStatus] = useState<OnboardingStatus | null>(null);
  const [facilityName, setFacilityName] = useState('');
  const [address, setAddress] = useState('');
  const [basePrice, setBasePrice] = useState(10000);
  const [rateRanks, setRateRanks] = useState<RateRankDraft[]>(initialRateRanks());
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

  const addRank = () => setRateRanks(items => [
    ...items,
    { label: String.fromCharCode(65 + items.length), price_jpy: Math.max(0, items[items.length - 1].price_jpy - 1000) },
  ]);

  const removeRank = (index: number) => setRateRanks(items => items
    .filter((_, itemIndex) => itemIndex !== index)
    .map((item, itemIndex) => ({ ...item, label: String.fromCharCode(65 + itemIndex) })));

  const submitSetup = async (event: FormEvent) => {
    event.preventDefault();
    const completedCompetitors = competitors.filter(item => item.name.trim() || item.url.trim());
    if (rateRanks.some((rank, index) => index > 0 && rateRanks[index - 1].price_jpy <= rank.price_jpy)) {
      setError('ランク価格はAから順に、前のランクより低い金額を入力してください。'); return;
    }
    if (!completedCompetitors.length || completedCompetitors.some(item => !item.name.trim() || !item.url.trim())) {
      setError('比較する宿の名前と予約サイトURLを、少なくとも1件入力してください。'); return;
    }
    const invalidUrl = completedCompetitors.map(item => checkOtaPropertyUrl(item.url)).find(item => !item.valid);
    if (invalidUrl) { setError(invalidUrl.message); return; }
    setBusy(true); setError('');
    try {
      await axios.post(`${apiBase}/onboarding`, {
        facility_name: facilityName,
        address,
        base_price: basePrice,
        min_price: rateRanks[rateRanks.length - 1].price_jpy,
        max_price: rateRanks[0].price_jpy,
        rate_ranks: rateRanks,
        competitors: completedCompetitors,
      }, { headers });
      onComplete();
    } catch (requestError: any) {
      setError(userFacingErrorMessage(requestError, '保存できませんでした。予約サイトのURLとランク価格を確認してください。'));
    } finally { setBusy(false); }
  };

  if (!status) return <main className="min-h-screen bg-slate-950 p-8"><p className="mx-auto max-w-md rounded-xl border border-indigo-800 bg-slate-900 p-5 text-sm text-indigo-100">初期設定を確認しています…</p>{error && <p className="mx-auto mt-3 max-w-md text-sm text-red-400">{error}</p>}</main>;

  const paymentActive = status.subscription_status === 'active';
  return <main className="min-h-screen bg-slate-950 p-4 text-slate-800 md:p-8">
    <section className="mx-auto max-w-3xl overflow-hidden rounded-2xl border border-indigo-200 bg-white shadow-2xl shadow-indigo-950/30">
      <div className="bg-gradient-to-r from-slate-950 via-indigo-950 to-violet-900 p-6 text-white">
        <p className="text-xs font-bold tracking-[0.25em] text-cyan-300">レベナビ 初期設定</p>
        <h1 className="mt-2 text-2xl font-bold">利用開始設定</h1>
        <p className="mt-2 text-sm text-indigo-100">施設の販売ルールを登録すると、競合データから日付ごとの参考ランクを算出します。</p>
      </div>
      <div className="p-6">
        {!paymentActive ? <div className="space-y-4"><p className="rounded-xl bg-blue-50 p-4 text-sm text-blue-900">月額プランに登録後、施設情報と競合URLを入力するとすぐに利用を開始できます。無料トライアルはありません。</p><button onClick={startCheckout} disabled={busy} className="rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-5 py-3 font-semibold text-white disabled:opacity-50">月額プランを開始する</button>{new URLSearchParams(window.location.search).get('checkout') === 'success' && <p className="text-sm text-amber-800">決済を確認しています。数秒後にこのページを再読み込みしてください。</p>}</div> : <form className="space-y-6" onSubmit={submitSetup}>
          <p className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-900">決済を確認しました。以下を入力すると利用を開始できます。</p>
          <div className="grid gap-4 md:grid-cols-2"><label className="text-sm font-semibold">施設名<input required value={facilityName} onChange={event => setFacilityName(event.target.value)} className="mt-1 w-full rounded-lg border p-2" /></label><label className="text-sm font-semibold">住所<input required value={address} onChange={event => setAddress(event.target.value)} className="mt-1 w-full rounded-lg border p-2" /></label></div>
          <div className="rounded-xl border border-indigo-100 bg-indigo-50/50 p-4">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between"><div><h2 className="font-semibold">販売ランクと価格</h2><p className="mt-1 text-xs text-slate-500">Aを最高価格として、競合の平均最安値に最も近いランクを参考表示します。</p></div><label className="text-sm font-semibold">判断基準価格<input required type="number" min="0" value={basePrice} onChange={event => setBasePrice(Number(event.target.value))} className="mt-1 w-full rounded-lg border bg-white p-2 sm:w-40" /></label></div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">{rateRanks.map((rank, index) => <div key={rank.label} className="flex items-center gap-3 rounded-xl border border-indigo-100 bg-white p-3 shadow-sm"><span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-violet-600 text-lg font-black text-white">{rank.label}</span><label className="flex-1 text-xs font-semibold text-slate-500">販売価格（円）<input required type="number" min="0" value={rank.price_jpy} onChange={event => setRateRanks(items => items.map((item, itemIndex) => itemIndex === index ? { ...item, price_jpy: Number(event.target.value) } : item))} className="mt-1 w-full rounded-lg border p-2 text-base font-bold text-slate-800" /></label>{index >= 4 && <button type="button" onClick={() => removeRank(index)} className="rounded-lg px-2 py-1 text-xs text-red-600 hover:bg-red-50">削除</button>}</div>)}</div>
            {rateRanks.length < 12 && <button type="button" onClick={addRank} className="mt-3 rounded-lg border border-indigo-200 bg-white px-3 py-2 text-sm font-semibold text-indigo-700 hover:bg-indigo-50">＋ ランク{String.fromCharCode(65 + rateRanks.length)}を追加</button>}
            <p className="mt-3 text-xs text-slate-500">最低価格・最高価格は、この表の末尾と先頭から自動設定されます。</p>
          </div>
          <div><h2 className="font-semibold">競合施設</h2><p className="mt-1 text-xs text-slate-500">通常プランでは、許諾済みOTAの施設URLを最大3件登録できます。</p><OtaUrlHelp value={competitors.find(item => item.url.trim())?.url} /><div className="mt-3 space-y-3">{competitors.map((competitor, index) => { const urlCheck = checkOtaPropertyUrl(competitor.url); return <div key={index} className="grid gap-2 rounded-xl border bg-slate-50 p-3 md:grid-cols-[1fr_2fr_auto]"><input required placeholder="競合施設名" value={competitor.name} onChange={event => setCompetitors(items => items.map((item, itemIndex) => itemIndex === index ? { ...item, name: event.target.value } : item))} className="rounded-lg border p-2 text-sm" /><label className="min-w-0"><input required type="url" placeholder="https://www.jalan.net/yad..." value={competitor.url} onChange={event => setCompetitors(items => items.map((item, itemIndex) => itemIndex === index ? { ...item, url: event.target.value } : item))} className={`w-full rounded-lg border p-2 text-sm ${competitor.url && !urlCheck.valid ? 'border-red-400 bg-red-50' : ''}`} />{competitor.url && <span className={`mt-1 block text-xs ${urlCheck.valid ? 'text-emerald-700' : 'text-red-700'}`}>{urlCheck.message}</span>}</label>{competitors.length > 1 && <button type="button" onClick={() => setCompetitors(items => items.filter((_, itemIndex) => itemIndex !== index))} className="rounded-lg border px-3 text-sm">削除</button>}</div>; })}</div>{competitors.length < 3 && <button type="button" onClick={() => setCompetitors(items => [...items, initialCompetitor()])} className="mt-3 text-sm font-semibold text-indigo-700 hover:underline">＋ 競合を追加</button>}</div>
          {error && <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-800">{error}</p>}
          <button disabled={busy} className="rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-5 py-3 font-semibold text-white shadow-lg shadow-indigo-200 disabled:opacity-50">設定を保存して分析を開始</button>
        </form>}
        {error && !paymentActive && <p role="alert" className="mt-4 rounded bg-red-50 p-3 text-sm text-red-800">{error}</p>}
      </div>
    </section>
  </main>;
}
