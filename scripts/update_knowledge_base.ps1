param(
    [string]$PythonExe = "D:\anaconde\envs\edu-agent\python.exe",
    [int]$MaxPagesPerSite = 0
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot
$env:PYTHONIOENCODING = "utf-8"

if (-not (Test-Path -LiteralPath $PythonExe)) {
    throw "Python executable not found: $PythonExe"
}

Write-Host "[1/3] Crawling Hebei Normal University public sites..."
if ($MaxPagesPerSite -le 0) {
    Write-Host "Page budget: unlimited per site"
} else {
    Write-Host "Page budget: $MaxPagesPerSite pages per site"
}
& $PythonExe "scripts\crawl_hebtu_sites.py" --max-pages-per-site $MaxPagesPerSite --clean-output
if ($LASTEXITCODE -ne 0) {
    throw "Crawler failed with exit code $LASTEXITCODE"
}

Write-Host "[2/3] Rebuilding knowledge chunks..."
& $PythonExe "scripts\build_chunks.py"
if ($LASTEXITCODE -ne 0) {
    throw "Chunk build failed with exit code $LASTEXITCODE"
}

Write-Host "[3/3] Rebuilding FAISS index with hashing backend..."
& $PythonExe "scripts\build_vector_index.py" --embedding-backend hashing
if ($LASTEXITCODE -ne 0) {
    throw "Vector index build failed with exit code $LASTEXITCODE"
}

Write-Host "Knowledge base update completed."
