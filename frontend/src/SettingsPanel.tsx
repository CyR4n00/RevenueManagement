import { useEffect, useState } from 'react';
import axios from 'axios';

interface Competitor { id: number; name: string; url: string; }
interface Facility { min_price: number; max_price: number; }
interface IntegrationStatus { environment: 'demo' | 'production'; apify_configured: boolean; line_messaging_configured: boolean; stripe_configured: boolean; simulation_enabled: boolean; }

export function SettingsPanel({ apiBase, onClose }: { apiBase: string; onClose: () => void }) {
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [facility, setFacility] = useState<Facility>({ min_price: 5000, max_price: 30000 });
  const [integration, setIntegration] = useState<IntegrationStatus | null>(null);
  const [adminKey, setAdminKey] = useState(sessionStorage.getItem('revenue-admin-key') || '');
  const [message, setMessage] = useState('');

  useEffect(() => { (async () => { try { const [competitorData, facilityData, integrationData] = await Promise.all([axios.get<Competitor[]>(`${apiBase}/competitors`), axios.get<Facility>(`${apiBase}/facility`), axios.get<IntegrationStatus>(`${apiBase}/integrations/status`)]); setCompetitors(competitorData.data); setFacility(facilityData.data); setIntegration(integrationData.data); } catch { setMessage('設定情報を読み込めませんでした。'); } })(); }, [apiBase]);

  const save = async () => {
    if (facility.min_price > facility.max_price) { setMessage('最低価格は最高価格以下にしてください。'); return; }
    try {
      sessionStorage.setItem('revenue-admin-key', adminKey);
      const headers = adminKey ? { 'X-Admin-Key': adminKey } : {};
      await Promise.all([axios.put(`${apiBase}/facility`, facility, { headers }), ...competitors.map(item => axios.put(`${apiBase}/competitors/${item.id}`, { name: item.name, url: item.url }, { headers }))]);
      onClose();
    } catch (error: any) { setMessage(error?.response?.status === 401 ? '管理キーが正しくありません。' : '保存に失敗しました。OTA URLとサーバー設定を確認してください。'); }
  };

  const startCheckout = async () => {
    try {
      const headers = adminKey ? { 'X-Admin-Key': adminKey } : {};
      const response = await axios.post<{ checkout_url: string }>(`${apiBase}/billing/checkout`, {}, { headers });
      window.location.assign(response.data.checkout_url);
    } catch { setMessage('Stripe Checkoutを開始できませんでした。STRIPE_SECRET_KEY、STRIPE_WEBHOOK_SECRET、STRIPE_PRICE_ID_PROを確認してください。'); }
  };

  return <section className="rounded-xl border bg-white p-6 shadow-sm"><div className="flex items-start justify-between gap-4"><div><h2 className="text-lg font-bold">運用設定</h2><p className="mt-1 text-sm text-slate-500">秘密情報は画面に保存せず、サーバー環境変数で管理します。</p></div><button onClick={onClose} aria-label="設定を閉じる" className="text-xl">×</button></div>{message && <p role="alert" className="mt-4 rounded bg-red-50 p-3 text-sm text-red-800">{message}</p>}
    <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-4"><Status title="環境" value={integration?.environment === 'production' ? '本番' : 'デモ'} ready={integration?.environment === 'production'} /><Status title="Apify" value={integration?.apify_configured ? '設定済み' : '未設定'} ready={integration?.apify_configured} /><Status title="LINE Messaging API" value={integration?.line_messaging_configured ? '設定済み' : '未設定'} ready={integration?.line_messaging_configured} /><Status title="Stripe" value={integration?.stripe_configured ? '設定済み' : '未設定'} ready={integration?.stripe_configured} /></div>
    <label className="mt-6 block text-sm font-semibold">管理キー（本番のみ必須）<input type="password" value={adminKey} onChange={event => setAdminKey(event.target.value)} className="mt-1 block w-full rounded border p-2" autoComplete="off" /></label>
    <div className="mt-6"><h3 className="font-semibold">競合施設</h3><div className="mt-3 space-y-3">{competitors.map((competitor, index) => <div key={competitor.id} className="grid gap-2 rounded border bg-slate-50 p-3 md:grid-cols-3"><label className="text-sm">名称<input value={competitor.name} onChange={event => setCompetitors(items => items.map(item => item.id === competitor.id ? { ...item, name: event.target.value } : item))} className="mt-1 w-full rounded border p-2" /></label><label className="text-sm md:col-span-2">OTA URL<input value={competitor.url} onChange={event => setCompetitors(items => items.map(item => item.id === competitor.id ? { ...item, url: event.target.value } : item))} className="mt-1 w-full rounded border p-2" /></label><span className="sr-only">競合 {index + 1}</span></div>)}</div></div>
    <div className="mt-6"><h3 className="font-semibold">価格ガードレール</h3><div className="mt-3 grid gap-3 md:grid-cols-2"><label className="text-sm">最低価格（円）<input type="number" min="0" value={facility.min_price} onChange={event => setFacility({ ...facility, min_price: Number(event.target.value) })} className="mt-1 w-full rounded border p-2" /></label><label className="text-sm">最高価格（円）<input type="number" min="0" value={facility.max_price} onChange={event => setFacility({ ...facility, max_price: Number(event.target.value) })} className="mt-1 w-full rounded border p-2" /></label></div></div>
    <p className="mt-6 rounded bg-slate-50 p-3 text-xs text-slate-600">Apifyトークン／Actor ID、LINE Channel Access Token／送信先User ID、Stripeの秘密鍵・Webhook Secret・Price IDはバックエンドの <code>.env</code> またはデプロイ先のシークレットに設定してください。LINE Notifyは使用しません。</p><div className="mt-6 flex flex-wrap justify-end gap-3"><button onClick={startCheckout} disabled={!integration?.stripe_configured} className="rounded border border-violet-600 px-5 py-2 font-semibold text-violet-700 disabled:cursor-not-allowed disabled:opacity-50">Stripeで契約を開始</button><button onClick={save} className="rounded bg-blue-600 px-5 py-2 font-semibold text-white">変更を保存</button></div>
  </section>;
}

function Status({ title, value, ready }: { title: string; value: string; ready?: boolean }) { return <div className="rounded border p-3"><p className="text-xs text-slate-500">{title}</p><p className={ready ? 'font-semibold text-emerald-700' : 'font-semibold text-amber-700'}>{value}</p></div>; }
