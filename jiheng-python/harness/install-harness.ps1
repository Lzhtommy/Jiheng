param(
    [string]$Source = "$PSScriptRoot\vendor\deepseek-harness"
)

$lock = Get-Content "$PSScriptRoot\UPSTREAM.lock"
$expected = ($lock | Where-Object { $_ -like 'commit=*' }).Split('=')[1]
if (-not (Test-Path -LiteralPath $Source)) {
    throw "Clone DeepSeek Harness at commit $expected to $Source before installation."
}
$actual = (& git -C $Source rev-parse HEAD).Trim()
if ($actual -ne $expected) {
    throw "Harness commit $actual does not match pinned commit $expected."
}
python -m pip install "$Source\python\sdk"
