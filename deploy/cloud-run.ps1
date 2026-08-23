param(
  [Parameter(Mandatory = $true)][string]$ProjectId,
  [string]$Region = "asia-northeast1",
  [string]$ServiceName = "revenavi",
  [Parameter(Mandatory = $true)][string]$StripePriceIdPro,
  [string]$StripePriceIdUpgrade = "",
  [Parameter(Mandatory = $true)][string]$AlertFromEmail,
  [switch]$EnableSchedules
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
  $bundledGcloud = "C:\Users\zerga\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin"
  if (Test-Path (Join-Path $bundledGcloud "gcloud.cmd")) {
    $env:PATH = "$bundledGcloud;$env:PATH"
  } else {
    throw "Google Cloud CLI (gcloud) is required. Install it and run 'gcloud auth login' first."
  }
}

$account = gcloud auth list --filter=status:ACTIVE --format="value(account)"
if (-not $account) {
  throw "No active Google Cloud account. Run 'gcloud auth login' first."
}

$secretNames = @(
  "revenavi-database-url",
  "revenavi-apify-token",
  "revenavi-stripe-secret-key",
  "revenavi-stripe-webhook-secret",
  "revenavi-resend-api-key"
)

gcloud config set project $ProjectId
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com cloudscheduler.googleapis.com iam.googleapis.com

foreach ($secretName in $secretNames) {
  gcloud secrets describe $secretName --project $ProjectId | Out-Null
}

$runtimeAccount = "$ServiceName-runtime"
$runtimeEmail = "$runtimeAccount@$ProjectId.iam.gserviceaccount.com"
$runtimeExists = gcloud iam service-accounts describe $runtimeEmail --format="value(email)" 2>$null
if (-not $runtimeExists) {
  gcloud iam service-accounts create $runtimeAccount --display-name="Revenavi runtime"
}
gcloud projects add-iam-policy-binding $ProjectId --member "serviceAccount:$runtimeEmail" --role roles/secretmanager.secretAccessor

$repository = "revenavi"
$repositoryExists = gcloud artifacts repositories describe $repository --location $Region --format="value(name)" 2>$null
if (-not $repositoryExists) {
  gcloud artifacts repositories create $repository --repository-format=docker --location=$Region --description="Revenavi production images"
}

$buildAccount = "$ServiceName-build"
$buildEmail = "$buildAccount@$ProjectId.iam.gserviceaccount.com"
$buildExists = gcloud iam service-accounts describe $buildEmail --format="value(email)" 2>$null
if (-not $buildExists) {
  gcloud iam service-accounts create $buildAccount --display-name="Revenavi build"
}
$buildMember = "serviceAccount:$buildEmail"
$sourceBucket = "gs://$ProjectId`_cloudbuild"
gcloud storage buckets add-iam-policy-binding $sourceBucket --member $buildMember --role roles/storage.objectAdmin
gcloud storage buckets add-iam-policy-binding $sourceBucket --member $buildMember --role roles/storage.legacyBucketReader
gcloud artifacts repositories add-iam-policy-binding $repository --location $Region --member $buildMember --role roles/artifactregistry.writer

$tag = Get-Date -Format "yyyyMMdd-HHmmss"
$image = "$Region-docker.pkg.dev/$ProjectId/$repository/$ServiceName`:$tag"
gcloud builds submit --config cloudbuild.yaml --service-account "projects/$ProjectId/serviceAccounts/$buildEmail" --substitutions "_IMAGE=$image" .

$safeEnvironment = "^|^" + (@(
  "APP_ENV=production",
  "SUPABASE_URL=https://jkotxfpqabxoseruvjsl.supabase.co",
  "SUPABASE_PUBLISHABLE_KEY=sb_publishable_wGJiBWtORaSpC35f7VHBhw_B4Vilk75",
  "SUPABASE_AUTH_REQUIRED=true",
  "ALLOW_SIMULATED_DATA=false",
  "DEMO_BYPASS_BILLING=false",
  "ALERT_FROM_EMAIL=$AlertFromEmail",
  "SCHEDULER_ENABLED=false",
  "SYNC_LOOKAHEAD_DAYS=90",
  "DAILY_SYNC_HOURS=9,18",
  "APIFY_ACTOR_BOOKING=",
  "APIFY_ACTOR_AIRBNB=",
  "APIFY_ACTOR_JALAN=gdqGtoOxUubNQt6r6",
  "APIFY_ACTOR_RAKUTEN=m86AxhyX5ImYCBM3x",
  "OTA_STATUS_BOOKING=pending",
  "OTA_STATUS_AIRBNB=pending",
  "OTA_STATUS_JALAN=approved",
  "OTA_STATUS_RAKUTEN=approved",
  "STRIPE_PRICE_ID_PRO=$StripePriceIdPro",
  "STRIPE_PRICE_ID_UPGRADE=$StripePriceIdUpgrade"
) -join "|")

$secretBindings = @(
  "DATABASE_URL=revenavi-database-url:latest",
  "APIFY_API_TOKEN=revenavi-apify-token:latest",
  "STRIPE_SECRET_KEY=revenavi-stripe-secret-key:latest",
  "STRIPE_WEBHOOK_SECRET=revenavi-stripe-webhook-secret:latest",
  "RESEND_API_KEY=revenavi-resend-api-key:latest"
) -join ","

gcloud run deploy $ServiceName --image $image --region $Region --platform managed --allow-unauthenticated --service-account $runtimeEmail --port 8080 --cpu 1 --memory 1Gi --min-instances 0 --max-instances 3 --concurrency 40 --timeout 300 --set-env-vars $safeEnvironment --set-secrets $secretBindings

$serviceUrl = gcloud run services describe $ServiceName --region $Region --format="value(status.url)"
gcloud run services update $ServiceName --region $Region --update-env-vars "FRONTEND_APP_URL=$serviceUrl,CORS_ORIGINS=$serviceUrl"

$jobEnvironment = $safeEnvironment + "|FRONTEND_APP_URL=$serviceUrl|CORS_ORIGINS=$serviceUrl"
$refreshJob = "$ServiceName-refresh"
$futureJob = "$ServiceName-future"
gcloud run jobs deploy $refreshJob --image $image --region $Region --service-account $runtimeEmail --command python --args sync_job.py,--mode,refresh --set-env-vars $jobEnvironment --set-secrets $secretBindings --task-timeout 30m --max-retries 1
gcloud run jobs deploy $futureJob --image $image --region $Region --service-account $runtimeEmail --command python --args sync_job.py,--mode,future --set-env-vars $jobEnvironment --set-secrets $secretBindings --task-timeout 30m --max-retries 1

$schedulerAccount = "$ServiceName-scheduler"
$schedulerEmail = "$schedulerAccount@$ProjectId.iam.gserviceaccount.com"
$schedulerExists = gcloud iam service-accounts describe $schedulerEmail --format="value(email)" 2>$null
if (-not $schedulerExists) {
  gcloud iam service-accounts create $schedulerAccount --display-name="Revenavi Cloud Scheduler"
}
gcloud run jobs add-iam-policy-binding $refreshJob --region $Region --member "serviceAccount:$schedulerEmail" --role roles/run.invoker
gcloud run jobs add-iam-policy-binding $futureJob --region $Region --member "serviceAccount:$schedulerEmail" --role roles/run.invoker

function Set-SchedulerJob([string]$Name, [string]$RunJob, [string]$Schedule) {
  $uri = "https://$Region-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$ProjectId/jobs/$RunJob`:run"
  $exists = gcloud scheduler jobs describe $Name --location $Region --format="value(name)" 2>$null
  if ($exists) {
    gcloud scheduler jobs update http $Name --location $Region --schedule $Schedule --time-zone "Asia/Tokyo" --uri $uri --http-method POST --oauth-service-account-email $schedulerEmail
  } else {
    gcloud scheduler jobs create http $Name --location $Region --schedule $Schedule --time-zone "Asia/Tokyo" --uri $uri --http-method POST --oauth-service-account-email $schedulerEmail
  }
  if (-not $EnableSchedules) {
    gcloud scheduler jobs pause $Name --location $Region
  }
}

Set-SchedulerJob "$ServiceName-refresh-0900" $refreshJob "0 9 * * *"
Set-SchedulerJob "$ServiceName-future-1800" $futureJob "0 18 * * *"

Write-Host "Revenavi deployed: $serviceUrl"
Write-Host "Next: register $serviceUrl/webhooks/stripe in Stripe and add $serviceUrl/** to Supabase Auth redirect URLs."
if (-not $EnableSchedules) {
  Write-Host "Collection schedules were created PAUSED. Resume them after the Apify usage limit is raised and both Actors pass a production run."
}
