# Revenue Assistant

旅館・民泊向けの競合料金モニタリング、ガードレール付き価格提案、CSV出力を提供するレベニューマネジメントMVPです。営業デモからパイロット導入へ進めるため、実データ連携と運用上の安全策を備えています。

## 提供機能

- **Apify経由のOTAデータ取得**：Booking.com、Airbnb、じゃらん、楽天トラベル向けに、OTAごとに検証済みのActorを設定します。アプリ自身はOTAを直接スクレイピングしません。
- **レベニュータワー**：競合3施設程度の前日比を、上昇（赤）・下落（青）・満室（グレー）で一覧化します。
- **価格ガードレール**：最低・最高価格を必ず適用し、A〜Dランクと価格を提案します。
- **LINE Messaging API通知**：大幅な値動き・満室を通知します。LINE Notifyは利用しません。
- **PMS CSV出力**：標準CSVを提供します。ねっぱん！／手間いらず向けは、導入先の公式サンプルCSVをもとに検証済みプロファイルを追加する方式です。
- **Stripe Billing**：Stripe Checkoutによるサブスクリプション開始と、署名検証済みWebhookによる契約状態の同期を備えます。

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

## Supabase移行

`DATABASE_URL` にSupabaseのPostgreSQL接続文字列を設定できます。パイロットから本番へ移行する際は、Supabaseのバックアップ、RLS、ユーザー／施設テナント分離を有効にし、SQLite互換の自動移行ではなくレビュー済みのDBマイグレーションを適用してください。

## Stripe設定

Stripeのキーはクライアントへ渡さず、バックエンドのシークレットにのみ設定します。

```text
FRONTEND_APP_URL=https://app.example.com
STRIPE_SECRET_KEY=sk_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID_PRO=price_...
```

Stripe DashboardのWebhook Endpointには `POST /webhooks/stripe` を登録し、少なくとも `checkout.session.completed`、`customer.subscription.updated`、`customer.subscription.deleted` を送信してください。Webhook署名が正しくないイベントは拒否されます。Checkoutはサブスクリプション用のPrice IDのみをサーバー側で使うため、クライアントから価格を差し替えられません。

## 運用時の注意

- `.env` はGit管理しません。デプロイ先のSecret Managerまたは環境変数を利用してください。
- 本番ではCORSを正規のフロントエンドURLだけに制限し、`ADMIN_API_KEY` を設定します。
- 現行の「ねっぱん！／手間いらず」CSVは未検証テンプレートです。各社の公式仕様・対象顧客の読み込みサンプルで受入テスト後に `verified` としてください。
