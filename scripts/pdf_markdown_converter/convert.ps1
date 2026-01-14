# PDF to Markdown Converter using marker-pdf via uv
param(
    [string]$PdfPath,
    [string]$OutputDir,
    [string]$GeminiModel,
    [switch]$UseLlm,
    [switch]$ForceOcr,
    [Parameter(ValueFromRemainingArguments)]
    [string[]]$ExtraArgs
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Load .env file
$EnvFile = Join-Path $ScriptDir ".env"
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]*?)\s*=\s*(.+?)\s*$') {
            $key = $matches[1]
            $value = $matches[2] -replace '^["'']|["'']$', ''
            [Environment]::SetEnvironmentVariable($key, $value, 'Process')
        }
    }
}

# Get PDF path from arg or env or prompt
if (-not $PdfPath) {
    $PdfPath = $env:INPUT_PDF
}
if (-not $PdfPath) {
    $PdfPath = Read-Host "Enter path to PDF file"
}
if (-not $PdfPath) {
    Write-Error "No PDF path provided"
    exit 1
}

# Resolve to absolute path
$PdfPath = [System.IO.Path]::GetFullPath($PdfPath)

if (-not (Test-Path $PdfPath)) {
    Write-Error "PDF file not found: $PdfPath"
    exit 1
}

# Get output dir - marker automatically creates a subfolder named after the PDF
# So we pass the parent directory, and marker creates: [OutputDir]\[PdfName]\
if (-not $OutputDir) {
    $OutputDir = [System.IO.Path]::GetDirectoryName($PdfPath)
}
$FinalOutputDir = [System.IO.Path]::Combine($OutputDir, [System.IO.Path]::GetFileNameWithoutExtension($PdfPath))

# Check for API key and auto-enable LLM if available
$apiKey = $env:GOOGLE_API_KEY
if ($apiKey -and -not $UseLlm) {
    $UseLlm = $true
    Write-Host "GOOGLE_API_KEY found - LLM enhancement enabled" -ForegroundColor Green
}

# Get Gemini model from param or env
if (-not $GeminiModel) {
    $GeminiModel = $env:GEMINI_MODEL_NAME
}

Write-Host "Input:  $PdfPath"
Write-Host "Output: $FinalOutputDir (marker creates subfolder automatically)"
Write-Host "LLM:    $UseLlm"
if ($UseLlm -and $GeminiModel) {
    Write-Host "Model:  $GeminiModel"
}
Write-Host ""

# Build command arguments (no quotes - PowerShell handles them)
$markerArgs = @(
    'run'
    '--with'
    'marker-pdf'
    'marker_single'
    $PdfPath
    '--output_dir'
    $OutputDir
    '--output_format'
    'markdown'
)

if ($UseLlm) {
    $markerArgs += '--use_llm'
    if ($apiKey) {
        $markerArgs += '--gemini_api_key'
        $markerArgs += $apiKey
    }
    if ($GeminiModel) {
        $markerArgs += '--gemini_model_name'
        $markerArgs += $GeminiModel
    }
}

if ($ForceOcr) {
    $markerArgs += '--force_ocr'
}

if ($ExtraArgs) {
    $markerArgs += $ExtraArgs
}

# Print full command (with quotes for copy-paste)
$displayArgs = $markerArgs | ForEach-Object {
    if ($_ -match '\s') { "`"$_`"" } else { $_ }
}
$fullCommand = "uv $($displayArgs -join ' ')"
Write-Host "Executing command:" -ForegroundColor Cyan
Write-Host $fullCommand -ForegroundColor Yellow
Write-Host ""

# Run marker via uv
& uv @markerArgs

Write-Host ""
Read-Host "Press Enter to close"
