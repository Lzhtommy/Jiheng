param(
    [Parameter(Mandatory = $true)][string]$DshHome,
    [Parameter(Mandatory = $true)][string]$AppRoot,
    [Parameter(Mandatory = $true)][string]$HarnessSource
)

$profile = Join-Path $DshHome 'profiles\jiheng'
New-Item -ItemType Directory -Force -Path $profile | Out-Null
Copy-Item "$PSScriptRoot\jiheng.cordis.patch.yml" "$profile\cordis.patch.yml" -Force
$env:DSH_HOME = $DshHome
$env:JIHENG_APP_ROOT = $AppRoot
dsh --profile jiheng --dump-default-config | Out-Null
dsh plugin --profile jiheng add "file:$HarnessSource\packages\mcp\mcp-client"
