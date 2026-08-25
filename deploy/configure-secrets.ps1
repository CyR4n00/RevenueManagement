param(
  [Parameter(Mandatory = $true)][string]$ProjectId
)

$ErrorActionPreference = "Stop"

$gcloudCommand = Get-Command gcloud.cmd -ErrorAction SilentlyContinue
if (-not $gcloudCommand) {
  $gcloudCommand = Get-Command gcloud -ErrorAction SilentlyContinue
}
if ($gcloudCommand) {
  $gcloudPath = $gcloudCommand.Source
} else {
  $bundledGcloudPath = "C:\Users\zerga\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
  if (-not (Test-Path $bundledGcloudPath)) {
    throw "Google Cloud CLI (gcloud) is required."
  }
  $gcloudPath = $bundledGcloudPath
}

function Invoke-GcloudProcess([string]$Arguments, [string]$StandardInput = $null, [switch]$AllowFailure) {
  $startInfo = [Diagnostics.ProcessStartInfo]::new()
  if ([IO.Path]::GetExtension($gcloudPath) -ieq ".cmd") {
    $startInfo.FileName = $env:ComSpec
    $startInfo.Arguments = '/d /s /c ""{0}" {1}"' -f $gcloudPath, $Arguments
  } else {
    $startInfo.FileName = $gcloudPath
    $startInfo.Arguments = $Arguments
  }
  $startInfo.UseShellExecute = $false
  $startInfo.RedirectStandardOutput = $true
  $startInfo.RedirectStandardError = $true
  $startInfo.RedirectStandardInput = $null -ne $StandardInput

  $process = [Diagnostics.Process]::Start($startInfo)
  if ($null -ne $StandardInput) {
    $process.StandardInput.Write($StandardInput)
    $process.StandardInput.Close()
  }
  $standardOutput = $process.StandardOutput.ReadToEnd()
  $standardError = $process.StandardError.ReadToEnd()
  $process.WaitForExit()

  if ($process.ExitCode -ne 0 -and -not $AllowFailure) {
    throw "Google Cloud CLI failed: $standardError"
  }
  return [PSCustomObject]@{
    ExitCode = $process.ExitCode
    Output = $standardOutput.Trim()
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
  $describe = Invoke-GcloudProcess "secrets describe $Name --project $ProjectId --format=value(name)" -AllowFailure
  if ($describe.ExitCode -ne 0) {
    $null = Invoke-GcloudProcess "secrets create $Name --project $ProjectId --replication-policy=automatic"
  }
  $null = Invoke-GcloudProcess "secrets versions add $Name --project $ProjectId --data-file=-" -StandardInput $Value
}

$null = Invoke-GcloudProcess "config set project $ProjectId"
$null = Invoke-GcloudProcess "services enable secretmanager.googleapis.com --project $ProjectId"

$databaseUrl = Read-SecretValue "Supabase Session pooler connection string (port 5432)"
if ($databaseUrl.StartsWith("postgresql://")) {
  $databaseUrl = $databaseUrl.Replace("postgresql://", "postgresql+psycopg://")
} elseif ($databaseUrl.StartsWith("postgres://")) {
  $databaseUrl = $databaseUrl.Replace("postgres://", "postgresql+psycopg://")
}
if (-not $databaseUrl.StartsWith("postgresql+psycopg://")) {
  throw "The database connection string must be a PostgreSQL URI."
}

$apifyVersionResult = Invoke-GcloudProcess "secrets versions list revenavi-apify-token --project $ProjectId --filter=state=ENABLED --limit=1 --format=value(name)" -AllowFailure
if ($apifyVersionResult.ExitCode -ne 0 -or -not $apifyVersionResult.Output) {
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
