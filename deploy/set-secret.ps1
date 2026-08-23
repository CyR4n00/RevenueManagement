param(
  [Parameter(Mandatory = $true)][string]$ProjectId,
  [Parameter(Mandatory = $true)]
  [ValidateSet(
    "revenavi-database-url",
    "revenavi-apify-token",
    "revenavi-stripe-secret-key",
    "revenavi-stripe-webhook-secret",
    "revenavi-resend-api-key"
  )]
  [string]$Name
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

$secure = Read-Host "Value for $Name" -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
  $value = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
} finally {
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
}

if (-not $value) {
  throw "A value is required."
}

$valid = switch ($Name) {
  "revenavi-database-url" { $value -match '^postgres(ql)?(\+psycopg)?://' }
  "revenavi-apify-token" { $value.StartsWith("apify_api_") }
  "revenavi-stripe-secret-key" { $value -match '^sk_(test|live)_' }
  "revenavi-stripe-webhook-secret" { $value.StartsWith("whsec_") }
  "revenavi-resend-api-key" { $value.StartsWith("re_") }
}
if (-not $valid) {
  throw "The value format is invalid for $Name."
}
if ($Name -eq "revenavi-database-url") {
  $value = $value -replace '^postgresql://', 'postgresql+psycopg://'
  $value = $value -replace '^postgres://', 'postgresql+psycopg://'
}

$exists = gcloud secrets describe $Name --project $ProjectId --format="value(name)" 2>$null
if (-not $exists) {
  gcloud secrets create $Name --project $ProjectId --replication-policy automatic
}

$startInfo = [Diagnostics.ProcessStartInfo]::new()
$startInfo.FileName = "gcloud"
$startInfo.UseShellExecute = $false
$startInfo.RedirectStandardInput = $true
foreach ($argument in @("secrets", "versions", "add", $Name, "--project", $ProjectId, "--data-file=-")) {
  [void]$startInfo.ArgumentList.Add($argument)
}
$process = [Diagnostics.Process]::Start($startInfo)
$process.StandardInput.Write($value)
$process.StandardInput.Close()
$process.WaitForExit()
$value = $null
if ($process.ExitCode -ne 0) {
  throw "Failed to update Secret Manager secret: $Name"
}
Write-Host "Updated $Name without printing or saving its value."
