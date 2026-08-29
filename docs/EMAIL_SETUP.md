# レベナビ メール設定手順

## まず理解すること

メールは2種類あります。

1. **ログイン用メール**：登録確認、メールリンク、パスワード再設定。SupabaseからResend SMTPを使って送ります。
2. **価格アラート**：レベナビのサーバーからResend APIを使って送ります。

両方とも、実在する顧客へ安定して送るには、所有ドメインをResendで認証する必要があります。

## 1. Resendで送信ドメインを認証する

1. Resendへログインする。
2. `Domains` → `Add Domain` を開く。
3. 所有しているドメイン、または `auth.example.jp` のような送信用サブドメインを入力する。
4. Resendに表示されたSPFとDKIMのDNSレコードを、ドメイン管理会社のDNS画面へそのまま登録する。
5. Resendへ戻り、`Verify` を押す。
6. `Verified` になるまで待つ。
7. 可能であればDMARCも設定する。

認証用メールでは、開封・クリック計測を無効にします。計測によるURL書き換えがログインリンクを壊すことを避けるためです。

## 2. ResendのAPIキーを作る

1. Resendの `API Keys` を開く。
2. レベナビ専用キーを作る。
3. 表示された `re_` から始まる値を安全な場所で一度だけ扱う。

APIキーをチャット、メール、文書、GitHubへ貼らないでください。

## 3. SupabaseへSMTPを設定する

Supabaseで対象プロジェクト `jkotxfpqabxoseruvjsl` を開きます。

1. `Authentication` → `Emails` を開く。
2. `SMTP Settings` を開く。
3. カスタムSMTPを有効にする。
4. 次を入力する。

| 項目 | 入力内容 |
| --- | --- |
| 送信者のメールアドレス | `noreply@認証済みドメイン` |
| 送信者名 | `レベナビ` |
| ホスト | `smtp.resend.com` |
| ポート | `465` |
| ユーザー名 | `resend` |
| パスワード | ResendのAPIキー |
| ユーザーごとの最小間隔 | 最初は60秒 |

5. 保存する。
6. 自分のメールアドレスで登録確認とパスワード再設定を1回ずつ試す。

## 4. 認証メールを日本語化する

1. Supabaseの `Authentication` → `Emails` → `Templates` を開く。
2. `Confirm signup`、`Magic Link`、`Reset password` を順番に開く。
3. [日本語テンプレート](./supabase-email-templates.md)の件名と本文を貼る。
4. `{{ .ConfirmationURL }}` は消したり書き換えたりしない。
5. 保存後、各メールを実際に受け取り、公開版レベナビへ戻れることを確認する。

## 5. 漏えいパスワード防止を有効にする

1. Supabaseの `Authentication` → `Attack Protection` またはパスワード関連設定を開く。
2. `Leaked password protection` を有効にする。
3. 保存する。

この機能はSupabase Pro以上で利用します。無料プランで項目が選べない場合は、プラン変更後に設定します。

## 6. レベナビの価格アラートを接続する

Resendでドメインが `Verified` になった後に行います。

1. Resend APIキーをGoogle Secret Managerの `revenavi-resend-api-key` へ保存する。
2. Cloud Runの `ALERT_FROM_EMAIL` を、認証済みドメインの送信元（例：`alert@example.jp`）に設定する。
3. Cloud Runを再デプロイする。
4. レベナビの設定画面で「通知を有効にする」を選ぶ。
5. 価格アラートを発生させ、登録済みログインメールへ届くことを確認する。

## 一時的な社内テスト

Supabase標準メールは本番配信には使いません。標準SMTPは送信先と回数が強く制限され、新規の無料プロジェクトではテンプレート変更にも制約があります。独自ドメインの用意前に社内テストをする場合だけ、対象メールをSupabase組織のチームメンバーとして招待し、短時間に繰り返し送信しないでください。

`neosofia0613@gmail.com` に届かなかった場合は、アドレスのつづり、Supabase組織メンバーへの招待、2通/時の標準SMTP制限、迷惑メールを順番に確認します。

