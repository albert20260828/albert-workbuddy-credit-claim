#!/usr/bin/env bash
# Install albert-workbuddy-credit-claim into the WorkBuddy skills directory.
# Usage (macOS / Linux):
#   curl -fsSL https://raw.githubusercontent.com/albert20260828/albert-workbuddy-credit-claim/main/install.sh | bash
# Or just run this file directly.
set -euo pipefail

REPO="albert20260828/albert-workbuddy-credit-claim"
SKILLS="$HOME/.workbuddy/skills"
DEST="$SKILLS/albert-workbuddy-credit-claim"

mkdir -p "$SKILLS"

if [ -d "$DEST" ]; then
  echo "[*] 已存在，尝试更新..."
  if [ -d "$DEST/.git" ]; then
    git -C "$DEST" pull --ff-only
  else
    echo "[!] 非 git 克隆的副本，跳过更新。如需重装请先删除: $DEST"
  fi
  exit 0
fi

if command -v git >/dev/null 2>&1; then
  git clone "https://github.com/$REPO.git" "$DEST"
else
  echo "[*] 无 git，改用下载解压..."
  tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
  curl -fsSL "https://github.com/$REPO/archive/refs/heads/main.zip" -o "$tmp/awcc.zip"
  unzip -q "$tmp/awcc.zip" -d "$tmp"
  mv "$tmp/${REPO##*/}-main" "$DEST"
fi

echo "[+] 安装完成: $DEST"
echo "[+] 刷新/重启 WorkBuddy 后在技能列表即可看到 albert-workbuddy-credit-claim"
