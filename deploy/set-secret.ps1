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

$describe = Invoke-GcloudProcess "secrets describe $Name --project $ProjectId --format=value(name)" -AllowFailure
if ($describe.ExitCode -ne 0) {
  $null = Invoke-GcloudProcess "secrets create $Name --project $ProjectId --replication-policy=automatic"
}

$null = Invoke-GcloudProcess "secrets versions add $Name --project $ProjectId --data-file=-" -StandardInput $value
$value = $null
Write-Host "Updated $Name without printing or saving its value."
