# レベナビ

旅館・民泊向けの競合料金モニタリングと、ガードレール付き参考ランクを提供するレベニューマネジメントSaaSです。営業デモからパイロット導入へ進めるため、実データ連携と運用上の安全策を備えています。

## 提供機能

- **Apify経由のOTAデータ取得**：Booking.com、Airbnb、じゃらん、楽天トラベル向けに、OTAごとに検証済みのActorを設定します。アプリ自身はOTAを直接スクレイピングしません。
- **レベニュータワー**：競合3施設程度の前日比を、上昇（赤）・下落（青）・満室（グレー）で一覧化します。
- **価格ガードレール**：最低・最高価格を必ず適用し、施設が設定したA〜F等の価格表から参考ランクを表示します。
- **メール通知**：大幅な値動き・部屋なしを、確認済みのログインメールへ重複なく通知します。配信停止は施設設定から切り替えられます。
- **Stripe Billing**：Stripe Checkoutによるサブスクリプション開始と、署名検証済みWebhookによる契約状態の同期を備えます。
- **表示期間**：通常プランは3か月／6か月、アップグレードプランは1年間を表示できます。期間上限は画面だけでなくAPI側でも強制します。
- **低負荷の将来データ補完**：1日2回の許諾範囲内で、1回目は直近期間、2回目は将来31日分をローテーション取得します。長期カレンダーを一度に大量取得しません。

## ローカル起動

1. `backend/.env.example` を `backend/.env` にコピーし、必要な値を設定します。
2. `frontend/.env.example` を `frontend/.env` にコピーします。
3. バックエンドで仮想環境を作成し、`pip install -r requirements.txt` を実行します。
4. `uvicorn main:app --reload --port 8000` を実行します。
5. `frontend` で `pnpm install`、`pnpm start` を実行します。

デモでは `ALLOW_SIMULATED_DATA=true` で疑似データを利用できます。画面に明示されるため、実データと混同しません。本番では `APP_ENV=production` とし、`ALLOW_SIMULATED_DATA=false`、`ADMIN_API_KEY` の設定を必須にしてください。

## Apify設定

次をバックエンドのシークレットとして設定します。

```text
APIFY_API_TOKEN=
APIFY_ACTOR_BOOKING=
APIFY_ACTOR_AIRBNB=
APIFY_ACTOR_JALAN=
APIFY_ACTOR_RAKUTEN=
```

Actorは `startUrls`、`checkIn`、`checkOut`、`adults`、`currency` を受け取り、データセットに宿泊料金（`price`、`pricePerNight`、`amount` 等）または満室状態を返すよう検証してください。OTAの規約とActorの出力仕様は導入前に確認が必要です。

`OTA_STATUS_BOOKING`、`OTA_STATUS_AIRBNB`、`OTA_STATUS_JALAN`、`OTA_STATUS_RAKUTEN` はすべて初期値を `pending` とします。`approved` に明示変更したOTAだけがApifyを実行できます。顧客がURLを登録することと、OTAからデータ取得の許諾を得ることは別です。

## Supabase

本番では `DATABASE_URL` にSupabaseのSession pooler（port 5432）接続文字列を設定します。公開スキーマの全テーブルでRLSを有効にし、ユーザー／施設のテナント分離を適用します。SQLiteと疑似データはローカルデモ専用で、本番起動時に拒否されます。

## メール通知設定

通知先は、Supabase Authで確認済みのログインメールから自動設定されます。配信にはResendのAPIキーと、認証済み送信ドメインのFromアドレスを本番シークレットとして設定します。

```text
RESEND_API_KEY=re_...
ALERT_FROM_EMAIL=レベナビ <alerts@example.com>
```

## Stripe設定

Stripeのキーはクライアントへ渡さず、バックエンドのシークレットにのみ設定します。

```text
FRONTEND_APP_URL=https://app.example.com
STRIPE_SECRET_KEY=sk_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID_PRO=price_...
STRIPE_PRICE_ID_UPGRADE=price_...
```

Stripe DashboardのWebhook Endpointには `POST /webhooks/stripe` を登録し、少なくとも `checkout.session.completed`、`customer.subscription.updated`、`customer.subscription.deleted` を送信してください。Webhook署名が正しくないイベントは拒否されます。Checkoutはサブスクリプション用のPrice IDのみをサーバー側で使うため、クライアントから価格を差し替えられません。

## 運用時の注意

- `.env` はGit管理しません。デプロイ先のSecret Managerまたは環境変数を利用してください。
- 本番ではReactとAPIを同一Cloud Runサービスで配信し、CORSをその公開URLだけに制限します。
- CSV／サイトコントローラー連携は将来機能です。公式フォーマットと導入施設のサンプルを入手してから別途実装します。

## マニュアルと完成確認

- 顧客向けのやさしい操作説明：[`docs/CLIENT_GUIDE.md`](docs/CLIENT_GUIDE.md)
- 運営者向けの日常運用・障害対応：[`docs/OPERATOR_MANUAL.md`](docs/OPERATOR_MANUAL.md)
- 営業開始までの残作業：[`CHECKLIST.md`](CHECKLIST.md)
- 印刷・配布用PDF：[`output/pdf/`](output/pdf/)
- ページごとの画像：[`output/images/`](output/images/)

顧客向けマニュアルは、専門用語を避け、初めてパソコンを使う方でも順番に操作できる表現にしています。運営者向けマニュアルには、カード決済と振込の両方、データ取得、メール通知、契約停止、問い合わせ対応を記載しています。
