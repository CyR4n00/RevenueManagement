import { FormEvent, useEffect, useState } from 'react';
import axios from 'axios';
import { userFacingErrorMessage } from './errorMessages';

interface OperatorSummary {
  organizations: number;
  active_subscriptions: number;
  collection_runs_7d: number;
  failed_collection_runs_7d: number;
  last_success_at: string | null;
  collection_runs_month: number;
  monthly_run_limit: number;
}

interface OperatorAccount {
  organization_id: string;
  organization_name: string;
  facility_name: string | null;
  notification_email: string | null;
  subscription_status: string;
  current_period_end: string | null;
  payment_method: 'stripe' | 'bank_transfer' | 'none';
}

interface PaymentRecord {
  id: string;
  organization_id: string;
  customer_name: string;
  billing_month: string;
  paid_at: string | null;
  amount_jpy: number;
  service_end: string;
  status: string;
  note: string | null;
}

const dateOnly = (value: string | null) => value ? value.slice(0, 10) : '';

export function OperatorPanel({ apiBase, accessToken, onClose }: { apiBase: string; accessToken: string; onClose: () => void }) {
  const headers = { Authorization: `Bearer ${accessToken}` };
  const [summary, setSummary] = useState<OperatorSummary | null>(null);
  const [accounts, setAccounts] = useState<OperatorAccount[]>([]);
  const [payments, setPayments] = useState<PaymentRecord[]>([]);
  const [periodEnds, setPeriodEnds] = useState<Record<string, string>>({});
  const [organizationId, setOrganizationId] = useState('');
  const [billingMonth, setBillingMonth] = useState(new Date().toISOString().slice(0, 7) + '-01');
  const [paidAt, setPaidAt] = useState(new Date().toISOString().slice(0, 10));
  const [serviceEnd, setServiceEnd] = useState('');
  const [amount, setAmount] = useState('30000');
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const load = async () => {
    setError('');
    try {
      const [summaryResponse, accountsResponse, paymentsResponse] = await Promise.all([
        axios.get<OperatorSummary>(`${apiBase}/operator/summary`, { headers }),
        axios.get<OperatorAccount[]>(`${apiBase}/operator/accounts`, { headers }),
        axios.get<PaymentRecord[]>(`${apiBase}/operator/payments`, { headers }),
      ]);
      setSummary(summaryResponse.data);
      setAccounts(accountsResponse.data);
      setPayments(paymentsResponse.data);
      setPeriodEnds(Object.fromEntries(accountsResponse.data.map(account => [account.organization_id, dateOnly(account.current_period_end)])));
      if (!organizationId && accountsResponse.data[0]) setOrganizationId(accountsResponse.data[0].organization_id);
    } catch (caught) {
      setError(userFacingErrorMessage(caught, '運営情報を読み込めませんでした。'));
    }
  };

  useEffect(() => { void load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const updateSubscription = async (account: OperatorAccount, status: 'active' | 'inactive') => {
    if (account.payment_method === 'stripe') return;
    const end = periodEnds[account.organization_id];
    if (status === 'active' && !end) { setError('利用を開始する場合は利用期限を入力してください。'); return; }
    setBusy(true); setError(''); setMessage('');
    try {
      await axios.put(`${apiBase}/operator/accounts/${account.organization_id}/subscription`, {
        status,
        current_period_end: status === 'active' ? `${end}T23:59:59+09:00` : null,
      }, { headers });
      setMessage(status === 'active' ? '振込契約を利用可能にしました。' : '利用を停止しました。');
      await load();
    } catch (caught) {
      setError(userFacingErrorMessage(caught, '契約状態を変更できませんでした。'));
    } finally { setBusy(false); }
  };

  const addPayment = async (event: FormEvent) => {
    event.preventDefault();
    const account = accounts.find(item => item.organization_id === organizationId);
    if (!account) return;
    setBusy(true); setError(''); setMessage('');
    try {
      await axios.post(`${apiBase}/operator/payments`, {
        organization_id: organizationId,
        customer_name: account.facility_name || account.organization_name,
        billing_month: billingMonth,
        paid_at: paidAt,
        amount_jpy: Number(amount),
        service_end: serviceEnd,
        status: 'paid',
        note: note || null,
      }, { headers });
      setMessage('入金記録を保存しました。続けて、下の顧客一覧から利用期限を有効にしてください。');
      setNote('');
      await load();
    } catch (caught) {
      setError(userFacingErrorMessage(caught, '入金記録を保存できませんでした。'));
    } finally { setBusy(false); }
  };

  return <section className="flex max-h-[92vh] w-full max-w-6xl flex-col overflow-hidden rounded-2xl bg-slate-50 shadow-2xl">
    <header className="flex items-center justify-between bg-gradient-to-r from-slate-950 to-indigo-900 px-6 py-5 text-white"><div><p className="text-xs font-bold tracking-[.2em] text-cyan-300">運営者専用</p><h1 className="mt-1 text-2xl font-black">運営管理</h1><p className="mt-1 text-xs text-slate-300">振込入金、利用期限、データ取得状況を管理します。</p></div><button type="button" onClick={onClose} className="rounded-lg border border-white/20 px-3 py-2 font-bold" aria-label="閉じる">×</button></header>
    <div className="space-y-6 overflow-y-auto p-5 md:p-7">
      {error && <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p>}
      {message && <p role="status" className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{message}</p>}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
        {[['顧客数', summary?.organizations ?? '—'], ['利用中', summary?.active_subscriptions ?? '—'], ['7日間の取得', summary?.collection_runs_7d ?? '—'], ['7日間の失敗', summary?.failed_collection_runs_7d ?? '—'], ['今月の取得', summary ? `${summary.collection_runs_month}${summary.monthly_run_limit ? ` / ${summary.monthly_run_limit}` : ''}` : '—'], ['最終成功', summary?.last_success_at ? new Date(summary.last_success_at).toLocaleString('ja-JP') : 'なし']].map(([label, value]) => <article key={String(label)} className="rounded-xl border bg-white p-4"><p className="text-xs font-bold text-slate-500">{label}</p><p className="mt-2 text-xl font-black">{value}</p></article>)}
      </div>

      <form onSubmit={addPayment} className="rounded-xl border bg-white p-5"><h2 className="font-black">振込入金を記録</h2><p className="mt-1 text-xs text-slate-500">通帳などで着金を確認してから入力します。記録だけでは利用開始になりません。</p><div className="mt-4 grid gap-3 md:grid-cols-3">
        <label className="text-sm font-bold">顧客<select required value={organizationId} onChange={event => setOrganizationId(event.target.value)} className="mt-1 w-full rounded-lg border p-2"><option value="">選択してください</option>{accounts.map(account => <option key={account.organization_id} value={account.organization_id}>{account.facility_name || account.organization_name}</option>)}</select></label>
        <label className="text-sm font-bold">請求月<input required type="date" value={billingMonth} onChange={event => setBillingMonth(event.target.value)} className="mt-1 w-full rounded-lg border p-2" /></label>
        <label className="text-sm font-bold">入金日<input required type="date" value={paidAt} onChange={event => setPaidAt(event.target.value)} className="mt-1 w-full rounded-lg border p-2" /></label>
        <label className="text-sm font-bold">金額（円）<input required min="1" type="number" value={amount} onChange={event => setAmount(event.target.value)} className="mt-1 w-full rounded-lg border p-2" /></label>
        <label className="text-sm font-bold">利用期限<input required type="date" value={serviceEnd} onChange={event => setServiceEnd(event.target.value)} className="mt-1 w-full rounded-lg border p-2" /></label>
        <label className="text-sm font-bold">メモ<input value={note} onChange={event => setNote(event.target.value)} className="mt-1 w-full rounded-lg border p-2" placeholder="振込名義など" /></label>
      </div><button disabled={busy} className="mt-4 rounded-lg bg-indigo-600 px-5 py-2.5 font-bold text-white disabled:opacity-50">入金を記録する</button></form>

      <section className="rounded-xl border bg-white p-5"><h2 className="font-black">顧客・利用期限</h2><div className="mt-4 overflow-x-auto"><table className="w-full min-w-[850px] text-left text-sm"><thead><tr className="border-b bg-slate-50"><th className="p-3">施設</th><th className="p-3">メール</th><th className="p-3">支払方法</th><th className="p-3">状態</th><th className="p-3">利用期限</th><th className="p-3">操作</th></tr></thead><tbody>{accounts.map(account => <tr key={account.organization_id} className="border-b"><td className="p-3 font-bold">{account.facility_name || account.organization_name}</td><td className="p-3">{account.notification_email || '未登録'}</td><td className="p-3">{account.payment_method === 'stripe' ? 'カード' : account.payment_method === 'bank_transfer' ? '振込' : '未設定'}</td><td className="p-3">{account.subscription_status === 'active' ? '利用中' : '停止中'}</td><td className="p-3"><input type="date" disabled={account.payment_method === 'stripe'} value={periodEnds[account.organization_id] || ''} onChange={event => setPeriodEnds(values => ({ ...values, [account.organization_id]: event.target.value }))} className="rounded border p-2 disabled:bg-slate-100" /></td><td className="p-3"><div className="flex gap-2">{account.payment_method === 'stripe' ? <span className="text-xs text-slate-500">Stripeで管理</span> : <><button disabled={busy} onClick={() => void updateSubscription(account, 'active')} className="rounded bg-emerald-600 px-3 py-2 text-xs font-bold text-white">利用開始</button><button disabled={busy} onClick={() => void updateSubscription(account, 'inactive')} className="rounded bg-slate-700 px-3 py-2 text-xs font-bold text-white">停止</button></>}</div></td></tr>)}</tbody></table></div></section>

      <section className="rounded-xl border bg-white p-5"><h2 className="font-black">最近の入金台帳</h2><div className="mt-4 overflow-x-auto"><table className="w-full min-w-[700px] text-left text-sm"><thead><tr className="border-b bg-slate-50"><th className="p-3">請求月</th><th className="p-3">顧客</th><th className="p-3">入金日</th><th className="p-3">金額</th><th className="p-3">利用期限</th><th className="p-3">メモ</th></tr></thead><tbody>{payments.length ? payments.map(payment => <tr key={payment.id} className="border-b"><td className="p-3">{payment.billing_month}</td><td className="p-3 font-bold">{payment.customer_name}</td><td className="p-3">{payment.paid_at || '未入金'}</td><td className="p-3">¥{payment.amount_jpy.toLocaleString()}</td><td className="p-3">{payment.service_end}</td><td className="p-3">{payment.note || '—'}</td></tr>) : <tr><td colSpan={6} className="p-6 text-center text-slate-500">まだ記録はありません。</td></tr>}</tbody></table></div></section>
    </div>
  </section>;
}
