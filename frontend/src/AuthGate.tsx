import { FormEvent, useState } from 'react';
import { supabase } from './supabase';
import { userFacingErrorMessage } from './errorMessages';

type Mode = 'password' | 'link';

const redirectTo = () => `${window.location.origin}/`;

export const authErrorMessage = (message: string) => {
  if (/failed to fetch|network request failed/i.test(message)) {
    return '認証サーバーに接続できません。しばらく待ってから再読み込みしてください。';
  }
  const retryAfter = message.match(/security purposes.*after\s+(\d+)\s+seconds?/i);
  if (retryAfter) {
    return `セキュリティ保護のため、あと${retryAfter[1]}秒待ってから再度お試しください。`;
  }
  if (/email rate limit exceeded|rate limit/i.test(message)) {
    return 'メールの送信回数が上限に達しました。しばらく待ってから再度お試しください。';
  }
  if (/invalid login credentials/i.test(message)) {
    return 'メールアドレスまたはパスワードが正しくありません。';
  }
  if (/email not confirmed/i.test(message)) {
    return 'メールアドレスの確認が完了していません。確認メール内のリンクを押してください。';
  }
  if (/user already registered/i.test(message)) {
    return 'このメールアドレスはすでに登録されています。ログインをお試しください。';
  }
  return userFacingErrorMessage(message, 'ログイン処理で問題が起きました。入力内容を確認して、もう一度お試しください。');
};

export function AuthGate() {
  const [mode, setMode] = useState<Mode>('password');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const client = supabase;
  if (!client) return null;

  const run = async (operation: () => Promise<{ error: { message: string } | null }>, success: string) => {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const { error: authError } = await operation();
      if (authError) {
        setError(authErrorMessage(authError.message));
        return;
      }
      setMessage(success);
    } catch (caught) {
      const detail = caught instanceof Error ? caught.message : 'Unknown authentication error';
      setError(authErrorMessage(detail));
    } finally {
      setBusy(false);
    }
  };

  const passwordLogin = (event: FormEvent) => {
    event.preventDefault();
    void run(
      () => client.auth.signInWithPassword({ email, password }),
      'ログインしました。',
    );
  };

  const passwordSignup = () => void run(
    () => client.auth.signUp({ email, password, options: { emailRedirectTo: redirectTo() } }),
    '確認メールを送信しました。メール内のリンクを押して登録を完了してください。',
  );

  const magicLink = (event: FormEvent) => {
    event.preventDefault();
    void run(
    () => client.auth.signInWithOtp({ email, options: { emailRedirectTo: redirectTo(), shouldCreateUser: true } }),
      'ログイン用メールを送信しました。メール内のリンクを押してください。',
    );
  };

  const resetPassword = () => void run(
    () => client.auth.resetPasswordForEmail(email, { redirectTo: redirectTo() }),
    'パスワード再設定用のメールを送信しました。',
  );

  return <main className="min-h-screen bg-slate-50 p-4 text-slate-800 md:p-8">
    <section className="mx-auto mt-10 max-w-md rounded-xl border bg-white p-6 shadow-sm">
      <h1 className="text-2xl font-bold">レベナビ</h1>
      <p className="mt-2 text-sm text-slate-600">メールアドレスで安全にログインできます。</p>

      <div className="mt-6 grid grid-cols-2 rounded-lg bg-slate-100 p-1 text-sm font-semibold">
        <button type="button" onClick={() => { setMode('password'); setError(''); setMessage(''); }} className={`rounded-md px-3 py-2 ${mode === 'password' ? 'bg-white text-blue-700 shadow-sm' : 'text-slate-600'}`}>パスワード</button>
        <button type="button" onClick={() => { setMode('link'); setError(''); setMessage(''); }} className={`rounded-md px-3 py-2 ${mode === 'link' ? 'bg-white text-blue-700 shadow-sm' : 'text-slate-600'}`}>メールリンク</button>
      </div>

      {mode === 'password' ? <form className="mt-5 space-y-4" onSubmit={passwordLogin}>
        <label className="block text-sm font-semibold">メールアドレス<input required type="email" value={email} onChange={event => setEmail(event.target.value)} autoComplete="email" className="mt-1 w-full rounded border p-2" /></label>
        <label className="block text-sm font-semibold">パスワード<input required minLength={8} type="password" value={password} onChange={event => setPassword(event.target.value)} autoComplete="current-password" className="mt-1 w-full rounded border p-2" /></label>
        <button disabled={busy} className="w-full rounded bg-blue-600 px-4 py-2 font-semibold text-white disabled:opacity-50">ログイン</button>
        <div className="flex justify-between gap-3 text-sm"><button type="button" disabled={busy || !email || password.length < 8} onClick={passwordSignup} className="text-blue-700 hover:underline disabled:text-slate-400">新規登録</button><button type="button" disabled={busy || !email} onClick={resetPassword} className="text-blue-700 hover:underline disabled:text-slate-400">パスワードを忘れた場合</button></div>
      </form> : <form className="mt-5 space-y-4" onSubmit={magicLink}>
        <p className="rounded bg-blue-50 p-3 text-sm text-blue-900">パスワードは不要です。届いたメールのリンクを一度押すだけでログインできます。初回利用にも対応しています。</p>
        <label className="block text-sm font-semibold">メールアドレス<input required type="email" value={email} onChange={event => setEmail(event.target.value)} autoComplete="email" className="mt-1 w-full rounded border p-2" /></label>
        <button disabled={busy} className="w-full rounded bg-blue-600 px-4 py-2 font-semibold text-white disabled:opacity-50">メールでログインリンクを受け取る</button>
      </form>}

      {message && <p role="status" className="mt-4 rounded bg-emerald-50 p-3 text-sm text-emerald-800">{message}</p>}
      {error && <p role="alert" className="mt-4 rounded bg-red-50 p-3 text-sm text-red-800">{error}</p>}
      <p className="mt-5 text-xs leading-relaxed text-slate-500">パスワード方式とメールリンク方式は、同じメールアドレスの同じアカウントで併用できます。</p>
      <nav className="mt-5 flex flex-wrap gap-x-4 gap-y-2 border-t pt-4 text-xs text-slate-500"><a href="#terms" className="hover:text-blue-700">利用規約</a><a href="#privacy" className="hover:text-blue-700">プライバシー</a><a href="#commerce" className="hover:text-blue-700">特定商取引法表記</a><a href="#contact" className="hover:text-blue-700">お問い合わせ</a></nav>
    </section>
  </main>;
}
