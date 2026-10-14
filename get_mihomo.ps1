# Downloads mihomo (Windows amd64) for the real connectivity test.
# Tries China-friendly mirrors first, because github.com is often unreachable here.
$ErrorActionPreference = "Continue"
$ver  = "v1.19.32"
$file = "mihomo-windows-amd64-compatible-$ver.zip"
$urls = @(
  "https://ghfast.top/https://github.com/MetaCubeX/mihomo/releases/download/$ver/$file",
  "https://ghproxy.net/https://github.com/MetaCubeX/mihomo/releases/download/$ver/$file",
  "https://github.com/MetaCubeX/mihomo/releases/download/$ver/$file"
)
$root = $PSScriptRoot
$zip  = Join-Path $root "mihomo.zip"
$tmp  = Join-Path $root "_mihomo_tmp"

foreach ($u in $urls) {
  try {
    Write-Host "[*] downloading $u"
    Invoke-WebRequest -Uri $u -OutFile $zip -TimeoutSec 180
    if ((Get-Item $zip).Length -gt 1MB) { break }
    Write-Host "[!] suspiciously small file, trying next mirror"
  } catch {
    Write-Host "[!] failed: $($_.Exception.Message)"
  }
}

if (-not (Test-Path $zip) -or (Get-Item $zip).Length -lt 1MB) {
  Write-Host "[!] all mirrors failed. Download mihomo-windows-amd64-compatible-$ver.zip manually"
  Write-Host "    and put mihomo.exe next to this script."
  exit 1
}

if (Test-Path $tmp) { Remove-Item -Recurse -Force -LiteralPath $tmp }
Expand-Archive -Force -LiteralPath $zip -DestinationPath $tmp
$exe = Get-ChildItem -Path $tmp -Recurse -Filter "mihomo*.exe" | Select-Object -First 1
if (-not $exe) { Write-Host "[!] mihomo exe not found inside archive"; exit 1 }

Copy-Item -LiteralPath $exe.FullName -Destination (Join-Path $root "mihomo.exe") -Force
Remove-Item -Recurse -Force -LiteralPath $tmp
Remove-Item -Force -LiteralPath $zip
Write-Host "[OK] mihomo.exe is ready"