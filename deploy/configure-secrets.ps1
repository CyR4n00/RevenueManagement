param(
  [Parameter(Mandatory = $true)][string]$ProjectId
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
  $bundledGcloud = "C:\Users\zerga\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin"
  if (Test-Path (Join-Path $bundledGcloud "gcloud.cmd")) {
    $env:PATH = "$bundledGcloud;$env:PATH"
  } else {
    throw "Google Cloud CLI (gcloud) is required."
  }
}

function Read-SecretValue([string]$Prompt) {
  $secure = Read-Host $Prompt -AsSecureString
  $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
  try {
    return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
  } finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
  }
}

function Add-SecretVersion([string]$Name, [string]$Value) {
  $exists = gcloud secrets describe $Name --project $ProjectId --format="value(name)" 2>$null
  if (-not $exists) {
    gcloud secrets create $Name --project $ProjectId --replication-policy automatic
  }

  $arguments = @(
    "secrets", "versions", "add", $Name,
    "--project", $ProjectId,
    "--data-file=-"
  )
  $startInfo = [Diagnostics.ProcessStartInfo]::new()
  $startInfo.FileName = "gcloud"
  $startInfo.UseShellExecute = $false
  $startInfo.RedirectStandardInput = $true
  foreach ($argument in $arguments) {
    [void]$startInfo.ArgumentList.Add($argument)
  }
  $process = [Diagnostics.Process]::Start($startInfo)
  $process.StandardInput.Write($Value)
  $process.StandardInput.Close()
  $process.WaitForExit()
  if ($process.ExitCode -ne 0) {
    throw "Failed to update Secret Manager secret: $Name"
  }
}

gcloud config set project $ProjectId
gcloud services enable secretmanager.googleapis.com

$databaseUrl = Read-SecretValue "Supabase Transaction pooler connection string"
if ($databaseUrl.StartsWith("postgresql://")) {
  $databaseUrl = $databaseUrl.Replace("postgresql://", "postgresql+psycopg://")
} elseif ($databaseUrl.StartsWith("postgres://")) {
  $databaseUrl = $databaseUrl.Replace("postgres://", "postgresql+psycopg://")
}
if (-not $databaseUrl.StartsWith("postgresql+psycopg://")) {
  throw "The database connection string must be a PostgreSQL URI."
}

$apifyVersion = gcloud secrets versions list "revenavi-apify-token" --project $ProjectId --filter="state=ENABLED" --limit=1 --format="value(name)" 2>$null
if (-not $apifyVersion) {
  $apifyToken = Read-SecretValue "Apify API token"
  if (-not $apifyToken.StartsWith("apify_api_")) {
    throw "The Apify token format is invalid."
  }
}

$stripeSecret = Read-SecretValue "Stripe test secret key (sk_test_...)"
if (-not ($stripeSecret.StartsWith("sk_test_") -or $stripeSecret.StartsWith("sk_live_"))) {
  throw "The Stripe secret key format is invalid."
}

$webhookSecret = Read-SecretValue "Stripe webhook signing secret (Enter if not created yet)"
if (-not $webhookSecret) {
  $webhookSecret = "whsec_pending_configuration"
} elseif (-not $webhookSecret.StartsWith("whsec_")) {
  throw "The Stripe webhook signing secret format is invalid."
}

$resendApiKey = Read-SecretValue "Resend API key (re_...)"
if (-not $resendApiKey.StartsWith("re_")) {
  throw "The Resend API key format is invalid."
}

Add-SecretVersion "revenavi-database-url" $databaseUrl
if ($apifyToken) {
  Add-SecretVersion "revenavi-apify-token" $apifyToken
}
Add-SecretVersion "revenavi-stripe-secret-key" $stripeSecret
Add-SecretVersion "revenavi-stripe-webhook-secret" $webhookSecret
Add-SecretVersion "revenavi-resend-api-key" $resendApiKey

$databaseUrl = $null
$apifyToken = $null
$stripeSecret = $null
$webhookSecret = $null
$resendApiKey = $null
Write-Host "Secret Manager configuration completed. No secret values were written to this repository."
