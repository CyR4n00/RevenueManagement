# 楽天トラベル・じゃらんの運用

楽天トラベルとじゃらんは、サービス運営者が取得した書面許諾を前提に、
本番の有効なデータソースとして設定する。許諾内容は「Apify 等による自動
取得、商用 SaaS 内での保存・価格比較、1 日おおむね 2 回の取得」である。

## 収集の単位

- スケジューラーは日本時間の `DAILY_SYNC_HOURS`（標準: `9,18`）に起動する。
- 1 施設・1 OTA・1 回の収集サイクルにつき、Actor は 1 回だけ起動する。
- ダッシュボードで表示する複数の宿泊日は、その 1 回の Actor 実行内で順番に
  取得し、各日付を 1 レコードとして保存する。
- Actor はログイン、CAPTCHA 回避、プロキシ回転、無制限の再試行を行わない。

## 本番設定

`backend/.env` に次を設定する。値そのものは Git に保存しない。

```dotenv
APP_ENV=production
ALLOW_SIMULATED_DATA=false
APIFY_API_TOKEN=<service-owned token>
APIFY_ACTOR_RAKUTEN=<private Rakuten actor ID>
APIFY_ACTOR_JALAN=<private Jalan actor ID>
OTA_STATUS_RAKUTEN=approved
OTA_STATUS_JALAN=approved
OTA_STATUS_BOOKING=pending
OTA_STATUS_AIRBNB=pending
DAILY_SYNC_HOURS=9,18
DAILY_SYNC_MINUTE=0
SYNC_LOOKAHEAD_DAYS=7
```

`approved` かつ Actor ID と Apify token が揃う OTA だけを競合 URL として登録
できる。Booking.com と Airbnb は、別途許諾・運用条件が確定するまで
`pending` のままにする。

## 監査と停止

- Actor は Apify 上で private のまま運用する。
- 収集結果には宿泊日、最安値または満室、取得時刻、取得元を保存する。
- 取得条件が変わった場合は該当 OTA を直ちに `disabled` に変更する。既存の
  保存データを削除する必要がある場合は、許諾条件に沿って別途実施する。
- 新しい OTA を有効化する前に、許諾範囲、1 日あたりの収集回数、保存期間、
  表示・リンク表記の要否をこの文書と `.env` に反映する。
