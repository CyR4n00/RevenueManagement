import { useEffect, useState } from 'react';
import axios from 'axios';
import { userFacingErrorMessage } from './errorMessages';
import { checkOtaPropertyUrl, OtaUrlHelp } from './OtaUrlHelp';

interface Competitor { id: string; name: string | null; url: string; isNew?: boolean; }
interface RateRank { label: string; price_jpy: number; sort_order: number; }
interface Facility { min_price: number; max_price: number; rate_ranks: RateRank[]; }
interface IntegrationStatus { environment: 'demo' | 'production'; apify_configured: boolean; email_delivery_configured: boolean; stripe_configured: boolean; simulation_enabled: boolean; }
interface BillingStatus { plan: 'standard' | 'upgrade'; max_competitors: number; }
interface NotificationSettings { email: string; enabled: boolean; delivery_configured: boolean; }

export function SettingsPanel({ apiBase, accessToken, onClose }: { apiBase: string; accessToken: string; onClose: () => void }) {
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [facility, setFacility] = useState<Facility>({ min_price: 5000, max_price: 30000, rate_ranks: [] });
  const [integration, setIntegration] = useState<IntegrationStatus | null>(null);
  const [billing, setBilling] = useState<BillingStatus>({ plan: 'standard', max_competitors: 3 });
  const [notifications, setNotifications] = useState<NotificationSettings>({ email: '', enabled: true, delivery_configured: false });
  const [message, setMessage] = useState('');
  const [saving, setSaving] = useState(false);
  const headers = accessToken ? { Authorization: `Bearer ${accessToken}` } : {};

  useEffect(() => { void (async () => {
    try {
      const [competitorData, facilityData, integrationData, billingData, notificationData] = await Promise.all([
        axios.get<Competitor[]>(`${apiBase}/competitors`, { headers }),
        axios.get<Facility>(`${apiBase}/facility`, { headers }),
        axios.get<IntegrationStatus>(`${apiBase}/integrations/status`, { headers }),
        axios.get<BillingStatus>(`${apiBase}/billing/status`, { headers }),
        axios.get<NotificationSettings>(`${apiBase}/notification-settings`, { headers }),
      ]);
      const loaded = facilityData.data;
      if (!loaded.rate_ranks?.length) loaded.rate_ranks = [
        { label: 'A', price_jpy: loaded.max_price, sort_order: 0 },
        { label: 'B', price_jpy: Math.round(loaded.max_price * 0.67), sort_order: 1 },
        { label: 'C', price_jpy: Math.round(loaded.max_price * 0.34), sort_order: 2 },
        { label: 'D', price_jpy: loaded.min_price, sort_order: 3 },
      ];
      setCompetitors(competitorData.data); setFacility(loaded); setIntegration(integrationData.data); setBilling(billingData.data); setNotifications(notificationData.data);
    } catch { setMessage('設定情報を読み込めませんでした。'); }
  })(); }, [apiBase, accessToken]); // eslint-disable-line react-hooks/exhaustive-deps

  const updateRank = (index: number, price: number) => setFacility(current => ({
    ...current,
    rate_ranks: current.rate_ranks.map((rank, itemIndex) => itemIndex === index ? { ...rank, price_jpy: price } : rank),
  }));
  const addRank = () => setFacility(current => ({
    ...current,
    rate_ranks: [...current.rate_ranks, { label: String.fromCharCode(65 + current.rate_ranks.length), price_jpy: Math.max(0, current.rate_ranks[current.rate_ranks.length - 1].price_jpy - 1000), sort_order: current.rate_ranks.length }],
  }));
  const removeRank = (index: number) => setFacility(current => ({
    ...current,
    rate_ranks: current.rate_ranks.filter((_, itemIndex) => itemIndex !== index).map((rank, itemIndex) => ({ ...rank, label: String.fromCharCode(65 + itemIndex), sort_order: itemIndex })),
  }));

  const save = async () => {
    const ranks = facility.rate_ranks;
    if (ranks.some((rank, index) => index > 0 && ranks[index - 1].price_jpy <= rank.price_jpy)) { setMessage('ランク価格はAから順に、前のランクより低くしてください。'); return; }
    if (competitors.some(item => !item.name?.trim() || !item.url.trim())) { setMessage('追加する宿の名前と予約サイトURLを入力してください。'); return; }
    const invalidUrl = competitors.map(item => checkOtaPropertyUrl(item.url)).find(item => !item.valid);
    if (invalidUrl) { setMessage(invalidUrl.message); return; }
    setSaving(true); setMessage('');
    try {
      await Promise.all([
        axios.put(`${apiBase}/facility`, { min_price: ranks[ranks.length - 1].price_jpy, max_price: ranks[0].price_jpy, rate_ranks: ranks.map(({ label, price_jpy }) => ({ label, price_jpy })) }, { headers }),
        axios.put(`${apiBase}/notification-settings`, { enabled: notifications.enabled }, { headers }),
        ...competitors.map(item => item.isNew
          ? axios.post(`${apiBase}/competitors`, { name: item.name, url: item.url }, { headers })
          : axios.put(`${apiBase}/competitors/${item.id}`, { name: item.name || '競合施設', url: item.url }, { headers })),
      ]);
      onClose();
    } catch (requestError: any) { setMessage(userFacingErrorMessage(requestError, '保存に失敗しました。入力内容を確認してください。')); }
    finally { setSaving(false); }
  };

  const openPortal = async () => {
    try {
      const response = await axios.post<{ checkout_url: string }>(`${apiBase}/billing/portal`, {}, { headers });
      window.location.assign(response.data.checkout_url);
    } catch { setMessage('契約管理画面を開けませんでした。運営者へお問い合わせください。'); }
  };

  return <section role="dialog" aria-modal="true" aria-labelledby="settings-title" className="flex max-h-[92vh] w-full max-w-4xl flex-col overflow-hidden rounded-2xl border border-indigo-200 bg-white shadow-2xl">
    <div className="flex items-start justify-between gap-4 bg-gradient-to-r from-slate-950 via-indigo-950 to-violet-900 p-5 text-white"><div><p className="text-xs font-bold tracking-[0.2em] text-cyan-300">管理メニュー</p><h2 id="settings-title" className="mt-1 text-xl font-bold">施設設定</h2><p className="mt-1 text-sm text-indigo-100">販売ランク・競合施設・外部連携を管理します。</p></div><button onClick={onClose} aria-label="設定を閉じる" className="rounded-lg border border-white/20 px-3 py-1.5 text-xl hover:bg-white/10">×</button></div>
    <div className="overflow-y-auto p-5 md:p-6">
      {message && <p role="alert" className="mb-5 rounded-xl bg-red-50 p-3 text-sm text-red-800">{message}</p>}
      <section><div className="flex items-end justify-between"><div><h3 className="font-bold">販売ランク</h3><p className="mt-1 text-xs text-slate-500">Aが最高価格です。E・F以降も必要に応じて追加できます。</p></div><span className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-bold text-indigo-700">{facility.rate_ranks.length}ランク</span></div><div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{facility.rate_ranks.map((rank, index) => <div key={rank.label} className="flex items-center gap-3 rounded-xl border border-indigo-100 bg-indigo-50/40 p-3"><span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-violet-600 text-lg font-black text-white">{rank.label}</span><label className="min-w-0 flex-1 text-xs font-semibold text-slate-500">販売価格<input type="number" min="0" value={rank.price_jpy} onChange={event => updateRank(index, Number(event.target.value))} className="mt-1 w-full rounded-lg border bg-white p-2 text-base font-bold text-slate-800" /></label>{index >= 4 && <button type="button" onClick={() => removeRank(index)} className="text-xs text-red-600">削除</button>}</div>)}</div>{facility.rate_ranks.length > 0 && facility.rate_ranks.length < 12 && <button type="button" onClick={addRank} className="mt-3 rounded-lg border border-indigo-200 px-3 py-2 text-sm font-semibold text-indigo-700 hover:bg-indigo-50">＋ ランク{String.fromCharCode(65 + facility.rate_ranks.length)}を追加</button>}</section>

      <section className="mt-7 border-t pt-6"><div className="flex flex-wrap items-end justify-between gap-3"><div><h3 className="font-bold">比較する宿</h3><p className="mt-1 text-xs text-slate-500">{billing.plan === 'upgrade' ? 'アップグレード' : '通常'}プラン：最大{billing.max_competitors}施設。長いURLは入力欄内でスクロールします。</p></div>{competitors.length < billing.max_competitors ? <button type="button" onClick={() => setCompetitors(items => [...items, { id: `new-${Date.now()}`, name: '', url: '', isNew: true }])} className="rounded-lg bg-indigo-50 px-3 py-2 text-sm font-bold text-indigo-700 hover:bg-indigo-100">＋ 比較する宿を追加</button> : <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700">登録上限 {competitors.length}/{billing.max_competitors}</span>}</div><OtaUrlHelp value={competitors.find(item => item.url.trim())?.url} /><div className="mt-3 space-y-3">{competitors.map(competitor => { const urlCheck = checkOtaPropertyUrl(competitor.url); return <div key={competitor.id} className="grid min-w-0 gap-3 rounded-xl border bg-slate-50 p-3 md:grid-cols-[minmax(160px,0.8fr)_minmax(0,2fr)_auto]"><label className="min-w-0 text-xs font-semibold text-slate-500">宿の名前<input value={competitor.name || ''} placeholder="比較する宿の名前" onChange={event => setCompetitors(items => items.map(item => item.id === competitor.id ? { ...item, name: event.target.value } : item))} className="mt-1 w-full min-w-0 rounded-lg border bg-white p-2 text-sm text-slate-800" /></label><label className="min-w-0 text-xs font-semibold text-slate-500">予約サイトURL<input value={competitor.url} placeholder="https://www.jalan.net/yad..." onChange={event => setCompetitors(items => items.map(item => item.id === competitor.id ? { ...item, url: event.target.value } : item))} className={`mt-1 w-full min-w-0 rounded-lg border bg-white p-2 text-sm text-slate-800 ${competitor.url && !urlCheck.valid ? 'border-red-400 bg-red-50' : ''}`} />{competitor.url && <span className={`mt-1 block text-xs ${urlCheck.valid ? 'text-emerald-700' : 'text-red-700'}`}>{urlCheck.message}</span>}</label>{competitor.isNew && <button type="button" onClick={() => setCompetitors(items => items.filter(item => item.id !== competitor.id))} className="self-end rounded-lg px-3 py-2 text-sm text-red-600 hover:bg-red-50">取消</button>}</div>; })}</div></section>

      <section className="mt-7 border-t pt-6"><h3 className="font-bold">メール通知</h3><p className="mt-1 text-xs text-slate-500">最初に登録・認証したログインメールを通知先として使用します。</p><div className="mt-3 flex flex-col gap-3 rounded-xl border bg-slate-50 p-4 sm:flex-row sm:items-center sm:justify-between"><div className="min-w-0"><p className="text-xs font-semibold text-slate-500">通知先（ログインメール）</p><p className="truncate font-bold text-slate-800">{notifications.email || '確認中…'}</p><p className="mt-1 text-xs text-amber-700">{notifications.delivery_configured ? 'メール配信に接続済みです。' : '通知先は保存済みです。実送信にはメール配信サービスの接続が必要です。'}</p></div><label className="flex items-center gap-2 text-sm font-semibold"><input type="checkbox" checked={notifications.enabled} onChange={event => setNotifications(current => ({ ...current, enabled: event.target.checked }))} />通知を有効にする</label></div></section>

      <details className="group mt-7 rounded-xl border"><summary className="flex cursor-pointer list-none items-center justify-between p-4"><div><h3 className="font-bold">連携・契約状態</h3><p className="mt-1 text-xs text-slate-500">通常は変更不要です。問題調査時に確認します。</p></div><span className="transition-transform group-open:rotate-180">▼</span></summary><div className="border-t p-4"><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><Status title="環境" value={integration?.environment === 'production' ? '本番' : 'デモ'} ready={integration?.environment === 'production'} /><Status title="データ取得" value={integration?.apify_configured ? '設定済み' : '未設定'} ready={integration?.apify_configured} /><Status title="通知先" value={notifications.email ? '設定済み' : '確認中'} ready={Boolean(notifications.email)} /><Status title="カード決済" value={integration?.stripe_configured ? '設定済み' : '未設定'} ready={integration?.stripe_configured} /></div></div></details>
    </div>
    <div className="flex flex-wrap justify-end gap-3 border-t bg-slate-50 p-4"><button onClick={openPortal} className="rounded-xl border border-violet-300 px-5 py-2 font-semibold text-violet-700">契約を管理</button><button onClick={save} disabled={saving || !facility.rate_ranks.length} className="rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-5 py-2 font-semibold text-white shadow-lg shadow-indigo-200 disabled:opacity-50">{saving ? '保存中…' : '変更を保存'}</button></div>
  </section>;
}

function Status({ title, value, ready }: { title: string; value: string; ready?: boolean }) { return <div className="rounded-xl border p-3"><p className="text-xs text-slate-500">{title}</p><p className={ready ? 'font-semibold text-emerald-700' : 'font-semibold text-amber-700'}>{value}</p></div>; }
