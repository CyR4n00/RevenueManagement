export type UrlCheck = { valid: boolean; message: string; ota?: string };

export function checkOtaPropertyUrl(value: string): UrlCheck {
  const raw = value.trim();
  if (!raw) return { valid: false, message: '' };
  let url: URL;
  try { url = new URL(raw); } catch { return { valid: false, message: '「https://」から始まるURLを、そのまま貼り付けてください。' }; }
  if (url.protocol !== 'https:') return { valid: false, message: '「https://」から始まるURLを使ってください。' };
  const host = url.hostname.toLowerCase();
  if (host === 'www.jalan.net' || host === 'jalan.net') {
    return /\/yad\d+(?:\/|$)/i.test(url.pathname)
      ? { valid: true, ota: 'じゃらんnet', message: 'じゃらんnetの施設ページとして確認できました。' }
      : { valid: false, ota: 'じゃらんnet', message: 'じゃらんnetの「宿のページ」を開き、URLに「/yad＋数字」が入ったものを貼ってください。' };
  }
  if (host === 'travel.rakuten.co.jp') {
    return /\/HOTEL\/\d+(?:\/|$)/i.test(url.pathname)
      ? { valid: true, ota: '楽天トラベル', message: '楽天トラベルの施設ページとして確認できました。' }
      : { valid: false, ota: '楽天トラベル', message: '楽天トラベルの「宿のページ」を開き、URLに「/HOTEL/数字」が入ったものを貼ってください。' };
  }
  if (host === 'www.booking.com' || host.endsWith('.booking.com')) {
    return /\/hotel\//i.test(url.pathname)
      ? { valid: true, ota: 'Booking.com', message: 'Booking.comの施設ページ形式です（現在は取得準備中です）。' }
      : { valid: false, ota: 'Booking.com', message: 'Booking.comの個別ホテルページを開き、URLに「/hotel/」が入ったものを貼ってください。' };
  }
  if (host === 'www.airbnb.com' || host === 'airbnb.com' || host.endsWith('.airbnb.com')) {
    return /\/rooms\/\d+(?:\/|$)/i.test(url.pathname)
      ? { valid: true, ota: 'Airbnb', message: 'Airbnbの宿泊施設ページ形式です（現在は取得準備中です）。' }
      : { valid: false, ota: 'Airbnb', message: 'Airbnbの個別宿泊施設ページを開き、URLに「/rooms/数字」が入ったものを貼ってください。' };
  }
  return { valid: false, message: '現在対応している予約サイト（じゃらんnet・楽天トラベル）の施設ページURLを貼ってください。' };
}

export function OtaUrlHelp({ value }: { value?: string }) {
  const checked = checkOtaPropertyUrl(value || '');
  return <div className="mt-3 rounded-xl border border-blue-100 bg-blue-50 p-4 text-xs leading-6 text-slate-700">
    <p className="font-bold text-blue-900">URLのコピー方法</p>
    <ol className="mt-1 list-decimal pl-5"><li>予約サイトで、比較したい宿そのもののページを開きます。</li><li>画面上部のアドレス欄を押して、URLを全部コピーします。</li><li>この入力欄へ貼り付けます。検索結果やGoogle・Yahoo!のURLは使いません。</li></ol>
    <div className="mt-2 rounded-lg bg-white p-3 font-mono text-[11px]"><p>じゃらん：<span className="break-all text-indigo-700">https://www.jalan.net/yad123456/</span></p><p>楽天：<span className="break-all text-indigo-700">https://travel.rakuten.co.jp/HOTEL/12345/12345.html</span></p></div>
    {value?.trim() && <p className={`mt-2 font-bold ${checked.valid ? 'text-emerald-700' : 'text-red-700'}`}>{checked.valid ? '✓ ' : '！ '}{checked.message}</p>}
  </div>;
}
