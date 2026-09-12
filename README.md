# WorkBuddy 每日积分领取（跨平台 · API 优先）

自动领取 WorkBuddy 客户端「Buddy加油站·今日礼包」积分，解放双手，不再漏签。支持 **Windows + macOS**，推荐**读本机登录 token 直调官方接口**，无需模拟鼠标点击、可后台无头运行。

---

## 功能特点

- 🔌 **API 优先**：读桌面客户端本地 token → 调官方签到接口，不抢前台、不怕全屏游戏夹鼠标、可无头运行
- 🪟🍎 **跨平台**：Windows 与 macOS 共用同一套领取逻辑（`scripts/claim_api.py`，纯标准库）
- ⏰ **原生定时**：macOS 用 `launchd` LaunchAgent 定时（睡眠错过会唤醒补跑）；Windows 端接 WorkBuddy 每日自动化
- 🔁 **幂等安全**：今日已领返回 `code=10001`，按成功处理，重复跑不翻车
- 🛡️ **凭证安全**：token 只读不写、不落日志；脚本也不存储
- 🆘 **兜底方案**：无 token 文件时，Windows 仍可走截图+真实点击（`scripts/claim_daily.py`）

---

## 快速开始

### 前提条件

- **Windows**：Python 3.x（推荐 WorkBuddy 托管 venv，纯标准库无需 Pillow）；客户端已登录
- **macOS**：系统 Python 3（实测 `/usr/bin/python3` 可直接跑）；客户端已登录
- 客户端必须处于已登录状态（token 由客户端写入本机）

### 方案：读 token 直调接口（推荐，Win + Mac 通用）

```bash
# Windows
"<managed-python>" "<skill>\scripts\claim_api.py"
# macOS
bash "<skill>/macos/checkin.sh"
```

`--dry-run` 只探测、不实际领取。

### Windows 兜底（截图 + 真实点击）

仅在找不到 token 文件的环境使用：

```bash
"<managed-python>" "<skill>\scripts\claim_daily.py"
```

### macOS 每日定时（launchd）

```bash
SK=~/.workbuddy/skills/albert-workbuddy-credit-claim
bash $SK/macos/setup_launchd.sh install            # 默认 11:00 + 20:00
bash $SK/macos/setup_launchd.sh install 09:30,13:00,21:00   # 自定义时刻
bash $SK/macos/setup_launchd.sh status             # 查看注册与最近执行
bash $SK/macos/setup_launchd.sh run                # 立即触发一次
bash $SK/macos/setup_launchd.sh remove             # 卸载
```

### 设为 Windows 每日自动化

在 WorkBuddy 建 recurring（`FREQ=DAILY;BYHOUR=8;BYMINUTE=0`），prompt 跑 `claim_api.py`，按 stdout 的 `RESULT` 一句话汇报。

---

## 安装（一行命令）

WorkBuddy 从 `~/.workbuddy/skills/` 目录加载技能，所以「安装」= 把仓库放进这个目录。**不是 npm 包，没有 `npm install` 通道**——下面这条命令等价于下载并放进去，装完刷新/重启 WorkBuddy 即可在技能列表看到。

- **Windows (PowerShell)**：
  ```powershell
  git clone https://github.com/albert20260828/albert-workbuddy-credit-claim.git "$env:USERPROFILE\.workbuddy\skills\albert-workbuddy-credit-claim"
  # 若没装 git，改用下载解压：
  irm https://github.com/albert20260828/albert-workbuddy-credit-claim/archive/refs/heads/main.zip -OutFile $env:TEMP\awcc.zip; Expand-Archive $env:TEMP\awcc.zip $env:TEMP\awcc -Force; Copy-Item "$env:TEMP\awcc\albert-workbuddy-credit-claim-main" "$env:USERPROFILE\.workbuddy\skills\albert-workbuddy-credit-claim" -Recurse -Force
  ```
- **macOS / Linux (bash)**：
  ```bash
  git clone https://github.com/albert20260828/albert-workbuddy-credit-claim.git ~/.workbuddy/skills/albert-workbuddy-credit-claim
  ```
- 或用仓库自带安装脚本：`install.ps1`（Windows）/ `install.sh`（macOS/Linux），重装时会自动 `git pull` 更新。

---

## RESULT / 退出码（API 路径）

| 退出码 | 含义 | 处理 |
| --- | --- | --- |
| 0 | 成功 / 今日已领（幂等） | 无需处理 |
| 2 | 配置错误（token 文件缺失/不可读） | 确认客户端已登录，或走兜底方案 |
| 3 | 网络错误 | 等下次重试 |
| 4 | 鉴权失败（token 过期） | 打开一次 WorkBuddy 客户端刷新 token |
| 5 | 接口返回非预期 | 看输出，字段可能已变更 |

---

## 目录结构

```
albert-workbuddy-credit-claim/
├── SKILL.md                          # 技能说明
├── README.md                         # 本文件
├── scripts/
│   ├── claim_api.py                  # 首选：跨平台读 token 直调接口
│   └── claim_daily.py                # 兜底：Windows 截图 + 真实点击
├── macos/
│   ├── workbuddy_daily_checkin.py    # 引擎（委托 claim_api.py）
│   ├── checkin.sh                    # launchd 入口
│   └── setup_launchd.sh              # launchd 安装/状态/触发/卸载
└── references/
    └── workflow.md                   # 完整工作流、接口勘察与死路清单
```

---

## 工作原理与避坑要点

- **token 文件位置**（两平台相对路径一致，仅根目录不同）：
  - Windows：`%LOCALAPPDATA%\CodeBuddyExtension\Data\Public\auth\workbuddy-desktop.info`
  - macOS：`~/Library/Application Support/CodeBuddyExtension/Data/Public/auth/workbuddy-desktop.info`
  - 字段取 `auth.accessToken` / `auth.tokenType` / `auth.domain`。
- **接口 host 是 `www.codebuddy.cn`**，不是 `workbuddy.cn`（后者经 APISIX 网关直接 401）。
- **不要用 UIAutomation / PostMessage**：Chromium 丢合成输入、Electron 无障碍树为空。
- **接口无补签**：当天完全离线则错过（连签重置），任何工具都绕不过。
- 详细勘察与全部走不通的尝试见 `references/workflow.md`。
