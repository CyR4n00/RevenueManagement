# レベナビ本番デプロイ

本番はReactとFastAPIを1つのCloud Runサービスとして公開します。同一オリジンにすることで、API URLの取り違えとCORS設定ミスを減らします。SQLiteと疑似価格は本番起動時に拒否されます。

## 事前に必要なもの

- 課金が有効なGoogle Cloudプロジェクト
- Google Cloud CLIでのログイン
- SupabaseのPostgreSQL接続文字列（Transaction pooler推奨）
- Apify API token
- StripeのSecret key、Webhook signing secret、月額プランのPrice ID
- ResendのAPI key、認証済み送信元メールアドレス

Secret Managerに次の5件を作成してください。値はGitHubやこのリポジトリへ保存しません。

- `revenavi-database-url`
- `revenavi-apify-token`
- `revenavi-stripe-secret-key`
- `revenavi-stripe-webhook-secret`
- `revenavi-resend-api-key`

PostgreSQL接続文字列はSQLAlchemy用に `postgresql+psycopg://...` で始めます。SupabaseのTransaction poolerを使う場合は、Dashboardの Connect 画面に表示される値を使用してください。

秘密情報は次のスクリプトでマスク入力できます。値は画面、チャット、リポジトリへ表示されません。Webhookをまだ作成していない場合は、その入力だけEnterで進めます。

```powershell
.\deploy\configure-secrets.ps1 -ProjectId "YOUR_GCP_PROJECT_ID"
```

1件だけ追加・更新する場合（公開URL確定後のStripe Webhook署名鍵など）は、次を使います。

```powershell
.\deploy\set-secret.ps1 -ProjectId "YOUR_GCP_PROJECT_ID" -Name "revenavi-stripe-webhook-secret"
```

## 公開

PowerShellでリポジトリ直下から実行します。

```powershell
.\deploy\cloud-run.ps1 -ProjectId "YOUR_GCP_PROJECT_ID" -StripePriceIdPro "price_..." -StripePriceIdUpgrade "price_..." -AlertFromEmail "レベナビ <alerts@example.com>"
```

公開後は次を設定します。

1. Supabase AuthのSite URLをCloud Run URLへ変更し、`https://.../**`をRedirect URLsへ追加
2. Stripe Webhookに `https://.../webhooks/stripe` を登録
3. Webhookイベントは `checkout.session.completed`、`customer.subscription.updated`、`customer.subscription.deleted` を選択
4. `/health` と `/ready` が200を返すことを確認

## 定期取得

Webサービス内蔵のAPSchedulerはCloud Runで複数起動する可能性があるため、本番では無効にします。定期実行は同じイメージを使うCloud Run Jobを2本作成し、Cloud Schedulerから9時と18時に起動します。Apifyの月間上限を解除してActorの更新を完了してから有効化してください。
