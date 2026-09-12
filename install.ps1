# Install albert-workbuddy-credit-claim into the WorkBuddy skills directory.
# Usage (PowerShell):
#   irm https://raw.githubusercontent.com/albert20260828/albert-workbuddy-credit-claim/main/install.ps1 | iex
# Or just run this file directly.
$ErrorActionPreference = 'Stop'

$repo   = 'albert20260828/albert-workbuddy-credit-claim'
$skills = Join-Path $env:USERPROFILE '.workbuddy/skills'
$dest   = Join-Path $skills 'albert-workbuddy-credit-claim'

if (-not (Test-Path $skills)) { New-Item -ItemType Directory -Path $skills | Out-Null }

if (Test-Path $dest) {
    Write-Host "[*] 已存在，尝试更新 (git pull)..."
    if (Test-Path (Join-Path $dest '.git')) {
        git -C $dest pull --ff-only
    } else {
        Write-Host "[!] 非 git 克隆的副本，跳过更新。如需重装请先删除: $dest"
    }
    exit 0
}

if (Get-Command git -ErrorAction SilentlyContinue) {
    git clone "https://github.com/$repo.git" $dest
} else {
    $zip = Join-Path $env:TEMP 'awcc.zip'
    $tmp = Join-Path $env:TEMP 'awcc'
    if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
    Write-Host "[*] 无 git，改用下载解压..."
    Invoke-WebRequest "https://github.com/$repo/archive/refs/heads/main.zip" -OutFile $zip
    Expand-Archive $zip $tmp -Force
    Move-Item (Join-Path $tmp "$($repo.Split('/')[-1])-main") $dest
    Remove-Item $zip, $tmp -Recurse -Force
}

Write-Host "[+] 安装完成: $dest"
Write-Host "[+] 刷新/重启 WorkBuddy 后在技能列表即可看到 albert-workbuddy-credit-claim"
