param(
  [Parameter(Mandatory = $true)][string]$ProjectId,
  [string]$Region = "asia-northeast1",
  [string]$ServiceName = "revenavi",
  [Parameter(Mandatory = $true)][string]$StripePriceIdPro,
  [string]$StripePriceIdUpgrade = "",
  [string]$AlertFromEmail = "",
  [string]$OperatorEmails = "",
  [int]$ApifyMonthlyRunLimit = 0,
  [string]$BusinessName = "",
  [string]$BusinessRepresentative = "",
  [string]$BusinessAddress = "",
  [string]$BusinessPhone = "",
  [string]$SupportEmail = "",
  [string]$Image = "",
  [switch]$EnableSchedules
)

$ErrorActionPreference = "Stop"

$gcloudCommand = Get-Command gcloud.cmd -ErrorAction SilentlyContinue
if (-not $gcloudCommand) {
  $gcloudCommand = Get-Command gcloud -ErrorAction SilentlyContinue
}
if ($gcloudCommand) {
  $gcloudPath = $gcloudCommand.Source
} else {
  $gcloudPath = "C:\Users\zerga\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
  if (-not (Test-Path $gcloudPath)) {
    throw "Google Cloud CLI (gcloud) is required. Install it and run 'gcloud auth login' first."
  }
}

function Invoke-Gcloud {
  param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
  $previousPreference = $ErrorActionPreference
  $ErrorActionPreference = "SilentlyContinue"
  $combinedOutput = & $gcloudPath @Arguments 2>&1
  $exitCode = $LASTEXITCODE
  $ErrorActionPreference = $previousPreference
  $output = @($combinedOutput | Where-Object { $_ -isnot [Management.Automation.ErrorRecord] })
  $errorText = @($combinedOutput | Where-Object { $_ -is [Management.Automation.ErrorRecord] } | ForEach-Object { $_.ToString() }) -join "`n"
  if ($exitCode -ne 0) {
    throw "Google Cloud CLI failed (exit $exitCode): $($Arguments -join ' ')`n$errorText"
  }
  return $output
}

function Test-Gcloud {
  param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
  $previousPreference = $ErrorActionPreference
  $ErrorActionPreference = "SilentlyContinue"
  $combinedOutput = & $gcloudPath @Arguments 2>&1
  $exitCode = $LASTEXITCODE
  $ErrorActionPreference = $previousPreference
  if ($exitCode -ne 0) {
    return $null
  }
  return @($combinedOutput | Where-Object { $_ -isnot [Management.Automation.ErrorRecord] })
}

$account = Invoke-Gcloud auth list --filter=status:ACTIVE --format="value(account)"
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

$null = Invoke-Gcloud config set project $ProjectId
$null = Invoke-Gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com cloudscheduler.googleapis.com iam.googleapis.com

foreach ($secretName in $secretNames) {
  $null = Invoke-Gcloud secrets describe $secretName --project $ProjectId
}

$runtimeAccount = "$ServiceName-runtime"
$runtimeEmail = "$runtimeAccount@$ProjectId.iam.gserviceaccount.com"
$runtimeExists = Test-Gcloud iam service-accounts describe $runtimeEmail --format="value(email)"
if (-not $runtimeExists) {
  $null = Invoke-Gcloud iam service-accounts create $runtimeAccount --display-name="Revenavi runtime"
}
foreach ($secretName in $secretNames) {
  $null = Invoke-Gcloud secrets add-iam-policy-binding $secretName --project $ProjectId --member "serviceAccount:$runtimeEmail" --role roles/secretmanager.secretAccessor
}

$repository = "revenavi"
$repositoryExists = Test-Gcloud artifacts repositories describe $repository --location $Region --format="value(name)"
if (-not $repositoryExists) {
  $null = Invoke-Gcloud artifacts repositories create $repository --repository-format=docker --location=$Region --description="Revenavi production images"
}

$buildAccount = "$ServiceName-build"
$buildEmail = "$buildAccount@$ProjectId.iam.gserviceaccount.com"
$buildExists = Test-Gcloud iam service-accounts describe $buildEmail --format="value(email)"
if (-not $buildExists) {
  $null = Invoke-Gcloud iam service-accounts create $buildAccount --display-name="Revenavi build"
}
$buildMember = "serviceAccount:$buildEmail"
$sourceBucket = "gs://$ProjectId`_cloudbuild"
$null = Invoke-Gcloud storage buckets add-iam-policy-binding $sourceBucket --member $buildMember --role roles/storage.objectAdmin
$null = Invoke-Gcloud storage buckets add-iam-policy-binding $sourceBucket --member $buildMember --role roles/storage.legacyBucketReader
$null = Invoke-Gcloud artifacts repositories add-iam-policy-binding $repository --location $Region --member $buildMember --role roles/artifactregistry.writer

if (-not $Image) {
  $tag = Get-Date -Format "yyyyMMdd-HHmmss"
  $Image = "$Region-docker.pkg.dev/$ProjectId/$repository/$ServiceName`:$tag"
  $null = Invoke-Gcloud builds submit --config cloudbuild.yaml --service-account "projects/$ProjectId/serviceAccounts/$buildEmail" --substitutions "_IMAGE=$Image" .
}

$safeEnvironment = (@(
  "APP_ENV=production",
  "SUPABASE_URL=https://jkotxfpqabxoseruvjsl.supabase.co",
  "SUPABASE_PUBLISHABLE_KEY=sb_publishable_wGJiBWtORaSpC35f7VHBhw_B4Vilk75",
  "SUPABASE_AUTH_REQUIRED=true",
  "ALLOW_SIMULATED_DATA=false",
  "DEMO_BYPASS_BILLING=false",
  "ALERT_FROM_EMAIL=$AlertFromEmail",
  "SCHEDULER_ENABLED=false",
  "SYNC_LOOKAHEAD_DAYS=90",
  "APIFY_MONTHLY_RUN_LIMIT=$ApifyMonthlyRunLimit",
  "OPERATOR_EMAILS=$OperatorEmails",
  "BUSINESS_NAME=$BusinessName",
  "BUSINESS_REPRESENTATIVE=$BusinessRepresentative",
  "BUSINESS_ADDRESS=$BusinessAddress",
  "BUSINESS_PHONE=$BusinessPhone",
  "SUPPORT_EMAIL=$SupportEmail",
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
) -join ",")

$secretBindings = @(
  "DATABASE_URL=revenavi-database-url:latest",
  "APIFY_API_TOKEN=revenavi-apify-token:latest",
  "STRIPE_SECRET_KEY=revenavi-stripe-secret-key:latest",
  "STRIPE_WEBHOOK_SECRET=revenavi-stripe-webhook-secret:latest",
  "RESEND_API_KEY=revenavi-resend-api-key:latest"
) -join ","

$null = Invoke-Gcloud run deploy $ServiceName --image $Image --region $Region --platform managed --allow-unauthenticated --service-account $runtimeEmail --port 8080 --cpu 1 --memory 1Gi --min-instances 0 --max-instances 3 --concurrency 40 --timeout 300 --set-env-vars $safeEnvironment --set-secrets $secretBindings

$serviceUrl = Invoke-Gcloud run services describe $ServiceName --region $Region --format="value(status.url)"
$null = Invoke-Gcloud run services update $ServiceName --region $Region --update-env-vars "FRONTEND_APP_URL=$serviceUrl,CORS_ORIGINS=$serviceUrl"

$jobEnvironment = $safeEnvironment + ",FRONTEND_APP_URL=$serviceUrl,CORS_ORIGINS=$serviceUrl"
$refreshJob = "$ServiceName-refresh"
$futureJob = "$ServiceName-future"
$null = Invoke-Gcloud run jobs deploy $refreshJob --image $Image --region $Region --service-account $runtimeEmail --command python --args sync_job.py,--mode,refresh --set-env-vars $jobEnvironment --set-secrets $secretBindings --task-timeout 30m --max-retries 1
$null = Invoke-Gcloud run jobs deploy $futureJob --image $Image --region $Region --service-account $runtimeEmail --command python --args sync_job.py,--mode,future --set-env-vars $jobEnvironment --set-secrets $secretBindings --task-timeout 30m --max-retries 1

$schedulerAccount = "$ServiceName-scheduler"
$schedulerEmail = "$schedulerAccount@$ProjectId.iam.gserviceaccount.com"
$schedulerExists = Test-Gcloud iam service-accounts describe $schedulerEmail --format="value(email)"
if (-not $schedulerExists) {
  $null = Invoke-Gcloud iam service-accounts create $schedulerAccount --display-name="Revenavi Cloud Scheduler"
}
$null = Invoke-Gcloud run jobs add-iam-policy-binding $refreshJob --region $Region --member "serviceAccount:$schedulerEmail" --role roles/run.invoker
$null = Invoke-Gcloud run jobs add-iam-policy-binding $futureJob --region $Region --member "serviceAccount:$schedulerEmail" --role roles/run.invoker

function Set-SchedulerJob([string]$Name, [string]$RunJob, [string]$Schedule) {
  $uri = "https://$Region-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$ProjectId/jobs/$RunJob`:run"
  $exists = Test-Gcloud scheduler jobs describe $Name --location $Region --format="value(name)"
  if ($exists) {
    $null = Invoke-Gcloud scheduler jobs update http $Name --location $Region --schedule $Schedule --time-zone "Asia/Tokyo" --uri $uri --http-method POST --oauth-service-account-email $schedulerEmail
  } else {
    $null = Invoke-Gcloud scheduler jobs create http $Name --location $Region --schedule $Schedule --time-zone "Asia/Tokyo" --uri $uri --http-method POST --oauth-service-account-email $schedulerEmail
  }
  if (-not $EnableSchedules) {
    $null = Invoke-Gcloud scheduler jobs pause $Name --location $Region
  }
}

Set-SchedulerJob "$ServiceName-refresh-0900" $refreshJob "0 9 * * *"
Set-SchedulerJob "$ServiceName-future-1800" $futureJob "0 18 * * *"

Write-Host "Revenavi deployed: $serviceUrl"
Write-Host "Next: register $serviceUrl/webhooks/stripe in Stripe and add $serviceUrl/** to Supabase Auth redirect URLs."
if (-not $EnableSchedules) {
  Write-Host "Collection schedules were created PAUSED. Resume them after the Apify usage limit is raised and both Actors pass a production run."
}
