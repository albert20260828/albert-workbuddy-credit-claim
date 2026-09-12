---
name: albert-workbuddy-credit-claim
description: "Cross-platform (Windows + macOS) WorkBuddy daily credit claim (Buddy加油站·今日礼包). Preferred path: read the local desktop login token and call the official check-in API (no UI automation, works headless). macOS ships a launchd LaunchAgent for native scheduling. Windows can also use the API directly; a screenshot+real-click fallback (scripts/claim_daily.py) remains for environments where the token file is unavailable. Use when the user says 每天自动领取积分 / 自动签到 / 领 WorkBuddy 积分 / 领 Buddy加油站 / macOS 自动签到, or wants a recurring daily automation."
agent_created: true
---

# WorkBuddy 每日积分领取（跨平台 · API 优先）

自动领取 WorkBuddy 客户端「Buddy加油站·今日礼包」积分。**推荐方式是不模拟点击、直接读本机登录 token 调官方接口**——可在后台无头运行、不抢前台、不怕全屏游戏夹鼠标。macOS 用 launchd 做原生定时（睡眠错过会唤醒补跑）。

## 原理（两条路径）

### 路径 A：读 token 直调接口（推荐，Win + Mac 通用）
桌面客户端会在本机写一个登录 token 文件，脚本读取后用它调用：

```
POST https://<auth.domain>/v2/billing/meter/daily-checkin
Authorization: <auth.tokenType> <auth.accessToken>
```

- token 文件（两平台相对路径一致，仅根目录不同）：
  - Windows：`%LOCALAPPDATA%\CodeBuddyExtension\Data\Public\auth\workbuddy-desktop.info`
  - macOS：`~/Library/Application Support/CodeBuddyExtension/Data\Public\auth\workbuddy-desktop.info`
- 字段：`auth.accessToken` / `auth.tokenType`（通常 `Bearer`）/ `auth.domain`（= `www.codebuddy.cn`）。
- 接口幂等：今日已领返回 `code=10001 / msg=今天已签到，请明天再来` → 视为成功（退出码 0）。
- 注意 host 是 **codebuddy.cn**，不是 workbuddy.cn（后者经 APISIX 网关直接 401）。

### 路径 B：截图 + 真实点击（兜底，仅 Windows）
`scripts/claim_daily.py`：PrintWindow 截窗口 → 像素定位「立即领取」黑色按钮 → 真实鼠标点击 → 复验。仅在**找不到 token 文件**的环境作为兜底。详见 `references/workflow.md`。

## When to use

- 用户说「每天自动领取积分 / 自动签到 / 领 WorkBuddy 积分 / 领 Buddy加油站」。
- 用户要在 macOS 上配置/排查签到定时任务。
- 用户想点客户端里任意按钮（走路径 B）。

## How to use

### Windows（API 优先，路径 A）
用 WorkBuddy 托管 Python 直接跑：

```bash
"<managed-python>" "<skill>\scripts\claim_api.py"      # 推荐（读 token 直调接口）
"<managed-python>" "<skill>\scripts\claim_daily.py"   # 兜底（UI 点击）
```

`claim_api.py` 纯标准库，无需 Pillow；`--dry-run` 只探测不领取。

### macOS（launchd 定时，路径 A）
```bash
SK=~/.workbuddy/skills/albert-workbuddy-credit-claim
bash $SK/macos/checkin.sh                  # 立刻签到一次（幂等）
bash $SK/macos/checkin.sh --dry-run        # 只探测
bash $SK/macos/setup_launchd.sh install     # 安装定时器（默认 11:00 + 20:00）
bash $SK/macos/setup_launchd.sh status      # 查看注册状态与最近执行
bash $SK/macos/setup_launchd.sh run         # 经 launchd 立即触发一次
bash $SK/macos/setup_launchd.sh remove      # 卸载
```

### 设为每日自动化（Windows 端）
建 recurring 任务（`FREQ=DAILY;BYHOUR=8;BYMINUTE=0`），prompt 跑 `claim_api.py` 并按 stdout 的 `RESULT` 一句话汇报（成功静默 / 失败才展开）。

## RESULT / 退出码（路径 A）

| 退出码 | 含义 | 处理 |
| --- | --- | --- |
| 0 | 成功 / 今日已领（幂等） | 无需处理 |
| 2 | 配置错误（token 文件缺失/不可读） | 改用路径 B，或确认客户端已登录 |
| 3 | 网络错误 | 等下次重试 |
| 4 | 鉴权失败（token 过期） | **打开一次 WorkBuddy 客户端**刷新 token |
| 5 | 接口返回非预期 | 看输出，字段可能已变更 |

## Critical constraints

- **只用官方接口 + 本机 token，不要 UIAutomation / PostMessage**（Chromium 丢合成输入、Electron 无障碍树为空）。
- **token 文件路径和 host 必须按上表**：Windows=`%LOCALAPPDATA%`、Mac=`~/Library/Application Support`；host=`www.codebuddy.cn`。
- token 是敏感凭证：脚本只读不写、不落日志；本 skill 也不存储它。
- 接口无「补签」能力，当天 0–24 点完全离线则错过（连签重置），任何工具都绕不过。

## Resources

### scripts/
- `claim_api.py` — **首选**。跨平台：读 token 文件 → 调接口 → 解析 `code` 字段。纯标准库。
- `claim_daily.py` — 兜底（Windows UI 点击）。仅在无 token 文件时用。

### macos/
- `workbuddy_daily_checkin.py` — 引擎（委托 `scripts/claim_api.py`，单一实现）。
- `checkin.sh` — launchd 入口（定位引擎、写日志、限长）。
- `setup_launchd.sh` — launchd 安装 / 状态 / 手动触发 / 卸载。

### references/
- `workflow.md` — 完整工作流、接口勘察、以及为何放弃 UI 自动化 / 直连 Web API 的死路清单。
