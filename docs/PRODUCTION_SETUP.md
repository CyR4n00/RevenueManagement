# 本番設定チェックリスト

このアプリは、同じメールアドレスで「メール＋パスワード」と「メールのログインリンク」のどちらも使えます。ブラウザにはSupabaseの**Publishable key**だけを設定し、Secret key / Service role keyは絶対に設定しません。

## 1. Supabase Auth

Supabase Dashboardの **Authentication > Providers > Email** でメール認証を有効にします。以下も設定してください。

- Site URL: デプロイ先の `https://app.example.com`
- Redirect URLs: `https://app.example.com/**`（開発用には `http://localhost:3000/**` も追加）
- Email confirmation: 有効
- SMTP: 本番用の独自SMTPを設定

マジックリンク、確認メール、パスワード再設定メールはすべて上記URLへ戻ります。メールリンクは一度だけ使えるため、共有メールアドレスではなく利用者ごとのメールアドレスを推奨します。

## 2. 環境変数

`backend/.env`:

```dotenv
APP_ENV=production
DATABASE_URL=postgresql+psycopg://...
CORS_ORIGINS=https://app.example.com
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
SUPABASE_AUTH_REQUIRED=true
ALLOW_SIMULATED_DATA=false
FRONTEND_APP_URL=https://app.example.com
```

`frontend/.env`:

```dotenv
REACT_APP_API_URL=https://api.example.com
REACT_APP_SUPABASE_URL=https://your-project.supabase.co
REACT_APP_SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
```

`REACT_APP_` で始まる値はブラウザへ配布されます。Stripe secret key、Supabase Secret key、PostgreSQL接続文字列、Apify tokenはここへ置かないでください。

## 3. 利用開始フロー

1. 利用者がメール＋パスワードまたはメールリンクで認証する。
2. Stripe Checkoutで月額プランを契約する。無料トライアルは設定しない。
3. Stripe Webhookが契約を `active` にする。
4. 利用者が施設名・住所・基準価格・下限/上限・競合URLを入力する。
5. ダッシュボードを使い始める。

契約が有効になる前と、初期設定が完了する前はダッシュボードAPIを利用できません。

## 4. ApifyとOTAの許諾

Apify tokenとActor IDを`backend/.env`へ設定しただけでは本番取得は始まりません。各 `OTA_STATUS_*` は最初 `pending` のままにし、正式API・規約確認・書面許可を得たOTAだけを `approved` に変更します。`pending` の競合URLは保存されますが、Apifyは実行されません。

## 5. LINE通知

現在の `LINE_USER_ID` は単一のデモ送信先用です。複数顧客の本番通知では、各組織が自分のLINE送信先を接続して保存する導線を追加してから有効化します。共有の送信先へ複数顧客のアラートを送ることはありません。
