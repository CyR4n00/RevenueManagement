import { useEffect, useState } from 'react';
import axios from 'axios';

interface Competitor { id: string; name: string | null; url: string; }
interface Facility { min_price: number; max_price: number; }
interface OtaSource { key: string; name: string; status: 'pending' | 'approved' | 'disabled'; actor_configured: boolean; }
interface IntegrationStatus { environment: 'demo' | 'production'; apify_configured: boolean; line_messaging_configured: boolean; stripe_configured: boolean; simulation_enabled: boolean; ota_sources: OtaSource[]; }

export function SettingsPanel({ apiBase, accessToken, onClose }: { apiBase: string; accessToken: string; onClose: () => void }) {
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [facility, setFacility] = useState<Facility>({ min_price: 5000, max_price: 30000 });
  const [integration, setIntegration] = useState<IntegrationStatus | null>(null);
  const [message, setMessage] = useState('');
  const headers = accessToken ? { Authorization: `Bearer ${accessToken}` } : {};

  useEffect(() => { void (async () => {
    try {
      const [competitorData, facilityData, integrationData] = await Promise.all([
        axios.get<Competitor[]>(`${apiBase}/competitors`, { headers }),
        axios.get<Facility>(`${apiBase}/facility`, { headers }),
        axios.get<IntegrationStatus>(`${apiBase}/integrations/status`, { headers }),
      ]);
      setCompetitors(competitorData.data); setFacility(facilityData.data); setIntegration(integrationData.data);
    } catch { setMessage('設定情報を読み込めませんでした。'); }
  })(); }, [apiBase, accessToken]); // eslint-disable-line react-hooks/exhaustive-deps

  const save = async () => {
    if (facility.min_price > facility.max_price) { setMessage('最低価格は最高価格以下にしてください。'); return; }
    try {
      await Promise.all([
        axios.put(`${apiBase}/facility`, facility, { headers }),
        ...competitors.map(item => axios.put(`${apiBase}/competitors/${item.id}`, { name: item.name || '競合施設', url: item.url }, { headers })),
      ]);
      onClose();
    } catch (requestError: any) { setMessage(requestError?.response?.data?.detail || '保存に失敗しました。'); }
  };

  const openPortal = async () => {
    try {
      const response = await axios.post<{ checkout_url: string }>(`${apiBase}/billing/portal`, {}, { headers });
      window.location.assign(response.data.checkout_url);
    } catch { setMessage('契約管理画面を開けませんでした。'); }
  };

  return <section className="rounded-xl border bg-white p-6 shadow-sm"><div className="flex items-start justify-between gap-4"><div><h2 className="text-lg font-bold">施設設定</h2><p className="mt-1 text-sm text-slate-500">価格ガードレールと競合URLを変更できます。</p></div><button onClick={onClose} aria-label="設定を閉じる" className="text-xl">×</button></div>{message && <p role="alert" className="mt-4 rounded bg-red-50 p-3 text-sm text-red-800">{message}</p>}
    <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-4"><Status title="環境" value={integration?.environment === 'production' ? '本番' : 'デモ'} ready={integration?.environment === 'production'} /><Status title="Apify" value={integration?.apify_configured ? '設定済み' : '未設定'} ready={integration?.apify_configured} /><Status title="LINE Messaging API" value={integration?.line_messaging_configured ? '設定済み' : '未設定'} ready={integration?.line_messaging_configured} /><Status title="Stripe" value={integration?.stripe_configured ? '設定済み' : '未設定'} ready={integration?.stripe_configured} /></div>
    <div className="mt-5 rounded border border-amber-200 bg-amber-50 p-3"><p className="text-sm font-semibold text-amber-900">OTA取得の許諾状態</p><p className="mt-1 text-xs text-amber-800">許諾済みのOTAだけが本番でApifyを実行します。許諾待ちのURLは保存されますが、取得されません。</p><div className="mt-3 grid gap-2 md:grid-cols-2">{integration?.ota_sources.map(source => <div key={source.key} className="flex items-center justify-between rounded bg-white px-3 py-2 text-sm"><span>{source.name}</span><span className={source.status === 'approved' ? 'font-semibold text-emerald-700' : source.status === 'pending' ? 'font-semibold text-amber-700' : 'font-semibold text-slate-500'}>{source.status === 'approved' ? '許諾済み' : source.status === 'pending' ? '許諾待ち' : '停止中'}</span></div>)}</div></div>
    <div className="mt-6"><h3 className="font-semibold">競合施設</h3><div className="mt-3 space-y-3">{competitors.map(competitor => <div key={competitor.id} className="grid gap-2 rounded border bg-slate-50 p-3 md:grid-cols-3"><label className="text-sm">名称<input value={competitor.name || ''} onChange={event => setCompetitors(items => items.map(item => item.id === competitor.id ? { ...item, name: event.target.value } : item))} className="mt-1 w-full rounded border p-2" /></label><label className="text-sm md:col-span-2">OTA URL<input value={competitor.url} onChange={event => setCompetitors(items => items.map(item => item.id === competitor.id ? { ...item, url: event.target.value } : item))} className="mt-1 w-full rounded border p-2" /></label></div>)}</div></div>
    <div className="mt-6"><h3 className="font-semibold">価格ガードレール</h3><div className="mt-3 grid gap-3 md:grid-cols-2"><label className="text-sm">最低価格（円）<input type="number" min="0" value={facility.min_price} onChange={event => setFacility({ ...facility, min_price: Number(event.target.value) })} className="mt-1 w-full rounded border p-2" /></label><label className="text-sm">最高価格（円）<input type="number" min="0" value={facility.max_price} onChange={event => setFacility({ ...facility, max_price: Number(event.target.value) })} className="mt-1 w-full rounded border p-2" /></label></div></div>
    <div className="mt-6 flex flex-wrap justify-end gap-3"><button onClick={openPortal} className="rounded border border-violet-600 px-5 py-2 font-semibold text-violet-700">契約を管理</button><button onClick={save} className="rounded bg-blue-600 px-5 py-2 font-semibold text-white">変更を保存</button></div>
  </section>;
}

function Status({ title, value, ready }: { title: string; value: string; ready?: boolean }) { return <div className="rounded border p-3"><p className="text-xs text-slate-500">{title}</p><p className={ready ? 'font-semibold text-emerald-700' : 'font-semibold text-amber-700'}>{value}</p></div>; }
