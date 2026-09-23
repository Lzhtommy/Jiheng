$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$worldSource = Join-Path $projectRoot 'app\static'
$worldTarget = Join-Path $projectRoot 'jiheng_ai_flutter\assets\world'
$assetTarget = Join-Path $worldTarget 'assets'

New-Item -ItemType Directory -Path $assetTarget -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $worldSource 'procurement-journey.html') -Destination (Join-Path $worldTarget 'index.html') -ErrorAction Stop

foreach ($assetName in @(
    'battery-cell-hall-v1.png',
    'cen-workshop-owner-v1.png',
    'downstream-port-v1.png',
    'jiheng-world-logo.png',
    'materials-workshop-v1.png',
    'salt-lake-mine-v1.png'
)) {
    Copy-Item -LiteralPath (Join-Path (Join-Path $worldSource 'assets') $assetName) -Destination (Join-Path $assetTarget $assetName) -ErrorAction Stop
}

Write-Output 'World assets synchronized for Flutter.'
