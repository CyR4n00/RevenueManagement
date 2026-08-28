import { useEffect, useState } from 'react';
import axios from 'axios';

export type PublicPageName = 'terms' | 'privacy' | 'commerce' | 'contact';

interface LegalConfig {
  business_name: string;
  representative: string;
  address: string;
  phone: string;
  support_email: string;
  complete: boolean;
}

const titles: Record<PublicPageName, string> = { terms: '利用規約', privacy: 'プライバシーポリシー', commerce: '特定商取引法に基づく表記', contact: 'お問い合わせ' };

export function PublicPages({ apiBase, page }: { apiBase: string; page: PublicPageName }) {
  const [config, setConfig] = useState<LegalConfig | null>(null);
  useEffect(() => { void axios.get<LegalConfig>(`${apiBase}/public/legal-config`).then(response => setConfig(response.data)).catch(() => setConfig(null)); }, [apiBase]);
  const body = page === 'terms' ? <div className="space-y-5"><section><h2 className="font-bold">1. サービスについて</h2><p>レベナビは、予約サイトに掲載された競合施設の情報を整理し、宿泊料金を検討するための参考情報を提供するサービスです。表示される参考価格やランクは、販売成果を保証するものではありません。</p></section><section><h2 className="font-bold">2. ご利用時のお願い</h2><p>登録情報は正確に入力し、アカウントを第三者へ貸さないでください。取得元サイトの障害や仕様変更などにより、一時的に情報を取得できない場合があります。</p></section><section><h2 className="font-bold">3. 料金と解約</h2><p>利用料金は申込画面に表示します。解約後は契約期間の終了まで利用でき、その後は閲覧・取得を停止します。返金の取扱いは個別契約または申込画面の記載に従います。</p></section><section><h2 className="font-bold">4. 禁止事項</h2><p>不正アクセス、サービスの妨害、取得データの無断再販売、法令や第三者の権利に反する利用を禁止します。</p></section><section><h2 className="font-bold">5. 免責と変更</h2><p>重要な販売判断は、必ず各予約サイトや自施設の予約状況も確認したうえで行ってください。本規約を変更する場合は、サービス上などで事前にお知らせします。</p></section></div>
    : page === 'privacy' ? <div className="space-y-5"><section><h2 className="font-bold">取得する情報</h2><p>氏名または施設名、メールアドレス、契約・支払状況、登録した施設情報、操作・エラー記録を取り扱います。</p></section><section><h2 className="font-bold">利用目的</h2><p>本人確認、サービス提供、料金請求、重要なお知らせ、障害対応、品質改善、不正利用防止のために利用します。</p></section><section><h2 className="font-bold">外部サービス</h2><p>認証・データ保存にSupabase、決済にStripe、競合情報の取得にApify、メール送信にResendなどを利用します。必要な範囲で各サービスへ情報が送信されます。</p></section><section><h2 className="font-bold">保存と安全管理</h2><p>必要な期間に限って保存し、アクセス制限、暗号化された通信、バックアップなどの安全対策を行います。開示・訂正・削除の相談はお問い合わせ先へご連絡ください。</p></section></div>
    : page === 'commerce' ? <dl className="grid gap-3 sm:grid-cols-[13rem_1fr]">{[['販売事業者', config?.business_name], ['運営責任者', config?.representative], ['所在地', config?.address], ['電話番号', config?.phone], ['メールアドレス', config?.support_email], ['販売価格', '申込画面に表示します（月額制）'], ['商品代金以外の費用', 'インターネット接続料金などはお客様の負担です'], ['支払方法・時期', 'クレジットカードまたは銀行振込。カードは申込時、その後は契約更新時に決済します'], ['サービス提供時期', '契約および初期設定の完了後に利用できます'], ['解約', '次回更新前までにお問い合わせ先へご連絡ください']].map(([label, value]) => <div className="contents" key={label}><dt className="rounded bg-slate-100 p-3 font-bold">{label}</dt><dd className="p-3">{value || '正式販売前に設定します'}</dd></div>)}</dl>
    : <div className="space-y-4"><p>操作方法、ご契約、データ表示に関するご相談は、下記メールアドレスへご連絡ください。</p><p className="rounded-xl bg-indigo-50 p-5 text-lg font-bold text-indigo-800">{config?.support_email || '正式販売前にお問い合わせ先を設定します'}</p><p className="text-sm text-slate-600">施設名、登録したメールアドレス、困っている画面、発生した日時を添えていただくと、確認が早くなります。</p></div>;
  return <main className="min-h-screen bg-slate-950 p-4 text-slate-800 md:p-10"><article className="mx-auto max-w-3xl overflow-hidden rounded-2xl bg-white shadow-2xl"><header className="bg-gradient-to-r from-indigo-950 to-violet-800 p-7 text-white"><a href="#overview" className="text-sm text-cyan-200">← レベナビへ戻る</a><h1 className="mt-4 text-3xl font-black">{titles[page]}</h1><p className="mt-2 text-sm text-indigo-100">最終更新日：2026年8月29日</p></header><div className="p-6 leading-7 md:p-9">{config && !config.complete && <p className="mb-6 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">現在は正式販売前の準備中です。事業者情報が確定するまで、このページは確認用として表示しています。</p>}{body}</div><footer className="flex flex-wrap gap-4 border-t bg-slate-50 p-5 text-sm"><a href="#terms">利用規約</a><a href="#privacy">プライバシー</a><a href="#commerce">特定商取引法表記</a><a href="#contact">お問い合わせ</a></footer></article></main>;
}
