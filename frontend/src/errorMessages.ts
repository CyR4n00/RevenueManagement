const japaneseText = /[ぁ-んァ-ヶ一-龠々]/;

function detailFrom(error: unknown): string {
  if (typeof error === 'string') return error;
  if (!error || typeof error !== 'object') return '';
  const candidate = error as {
    message?: unknown;
    response?: { data?: { detail?: unknown } };
  };
  const detail = candidate.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (typeof candidate.message === 'string') return candidate.message;
  return '';
}

const translations: Array<[RegExp, string]> = [
  [/failed to fetch|network request failed|network error/i, '通信できませんでした。インターネット接続を確認して、もう一度お試しください。'],
  [/date must be yyyy-mm-dd/i, '日付の形式が正しくありません。'],
  [/competitor url must use https/i, '予約サイトのURLは「https://」から始まるものを入力してください。'],
  [/only configured ota domains are allowed/i, '現在対応している予約サイトのURLを入力してください。'],
  [/is not available for collection yet/i, 'この予約サイトは現在データ取得の準備中です。'],
  [/account setup has not started/i, '利用開始の設定がまだ始まっていません。'],
  [/only an owner or administrator/i, 'この設定を変更できる権限がありません。'],
  [/organization not found/i, '施設の契約情報が見つかりませんでした。'],
  [/maximum horizon of \d+ days/i, '現在のプランで表示できる期間を超えています。'],
  [/an active subscription is required/i, '利用を続けるには、ご契約の確認が必要です。'],
  [/facility setup has not been completed/i, '施設の初期設定が完了していません。'],
  [/market data is unavailable/i, '競合施設の最新データを取得できませんでした。保存済みデータをご確認ください。'],
  [/comparison_days must be/i, '比較期間の指定が正しくありません。'],
  [/supports up to \d+ competitors/i, '登録できる競合施設数の上限に達しています。'],
  [/competitor url is already registered/i, 'この競合施設のURLはすでに登録されています。'],
  [/competitor not found/i, '競合施設が見つかりませんでした。'],
  [/subscription is already active/i, 'このアカウントはすでに契約中です。'],
  [/stripe billing is not configured/i, '現在はカード決済の準備中です。運営者へお問い合わせください。'],
  [/no stripe customer is linked/i, 'この契約は画面から変更できません。運営者へお問い合わせください。'],
  [/unknown authentication error/i, 'ログイン処理で問題が起きました。もう一度お試しください。'],
];

export function userFacingErrorMessage(error: unknown, fallback: string): string {
  const detail = detailFrom(error).trim();
  if (!detail) return fallback;
  if (japaneseText.test(detail)) return detail;
  const translation = translations.find(([pattern]) => pattern.test(detail));
  return translation?.[1] || fallback;
}
