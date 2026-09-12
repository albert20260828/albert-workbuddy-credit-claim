# WorkBuddy 每日积分领取 —— 工作流与踩坑记录

## 需求形态
用户想要「每天自动领取 WorkBuddy 积分」。客户端入口是左下角浮动卡牌
「Buddy加油站·N期 / 今日可领 100 积分 / 立即领取」按钮。点击后弹 toast
「领取成功」，按钮变「今日已领」。每日 1 次，约 100 分/天（连续第 7 天有 10 倍大奖）。

## ✅ 正确路径：读本机 token 直调官方接口（首选，Win + Mac 通用）

桌面客户端会在本机写入一个登录 token 文件，里面带了访问令牌。脚本读它、直接调
官方签到接口即可，**不需要任何 UI 自动化**，可后台无头运行。

### token 文件位置（两平台相对路径一致，仅根目录不同）
- Windows：`%LOCALAPPDATA%\CodeBuddyExtension\Data\Public\auth\workbuddy-desktop.info`
- macOS：`~/Library/Application Support/CodeBuddyExtension/Data\Public\auth\workbuddy-desktop.info`

实测文件结构（字段已脱敏）：
```json
{
  "account": { "nickname": "Albert-AI 助教", "uin": 330103588671, "type": "personal", ... },
  "auth": {
    "accessToken": "<1337 字符>",
    "tokenType": "Bearer",
    "domain": "www.codebuddy.cn",
    "expiresAt": 1794363856569,
    "refreshExpiresAt": 1796955856569
  }
}
```
取 `auth.accessToken` + `auth.tokenType`（`Bearer`）+ `auth.domain`。

### 接口
```
POST https://<auth.domain>/v2/billing/meter/daily-checkin
Authorization: <auth.tokenType> <auth.accessToken>
Content-Type: application/json
```
- host 必须是 **codebuddy.cn**（见下方死路：workbuddy.cn 被 APISIX 网关 401）。
- 返回体用 JSON `code` 字段表达状态，**不看 HTTP 状态码**：
  - `code=0` → 成功
  - `code=10001` / `msg=今天已签到，请明天再来` → 今日已领（**幂等，按成功处理**）
  - 实测「已领」时 HTTP 是 **400**，所以解析时一定要以 `code` 字段为准。
- 退出码约定（路径 A）：`0` 成功/已领，`2` 配置错（token 缺失），`3` 网络错，
  `4` 鉴权失败（token 过期→打开客户端刷新），`5` 非预期返回。

### macOS 定时
用 `launchd` LaunchAgent（`macos/setup_launchd.sh`）：跑在 GUI 会话内、睡眠错过会
唤醒补跑、`launchctl kickstart` 可当场验证。plist 落在
`~/Library/LaunchAgents/com.albert.workbuddy.dailycheckin.plist`。

---

## ❌ 之前的误判（记录以正视听）
早期结论「Windows 本地拿不到 token，只能 UI 真实点击」是**错的**——当时只在
localStorage / Cookies 里找 JWT，没去翻客户端的数据目录。实际上 token 就是上面那个
`workbuddy-desktop.info` 文件，**Windows 端路径为 `%LOCALAPPDATA%\CodeBuddyExtension\...`**，
与 Mac 完全对应。因此 Windows 也应优先走 API 路径，UI 点击降级为兜底。

## 兜底路径：截图 + 真实点击（仅 Windows，无 token 文件时用）
`scripts/claim_daily.py`：EnumWindows 找 WorkBuddy 窗口 → `PrintWindow` 截窗口位图 →
像素扫描左 45%/下 28% 区域找「实心深色块」（R/G/B 均 <75，单行列连续 ≥35px，即黑色
「立即领取」按钮）→ 切前台 + 释放 ClipCursor + `SetCursorPos`+`mouse_event` 真实点击 →
再截一次复验。带 30 次抗游戏夹鼠标重试，点击前用 `WindowFromPoint` 校验落点归属 WorkBuddy
进程，做完归还鼠标/前台。

## 已验证走不通的死路（别再试）
- **UIAutomation / Inspect / UIA FindAll**：Electron 未开可访问性支持，树为空。
- **PostMessage(WM_LBUTTONDOWN/UP)**：Chromium 丢弃合成输入。
- **直连 Web 端 `https://www.workbuddy.cn/billing/meter/...`**：APISIX 网关直接 401。
  正确 host 是 **codebuddy.cn**（桌面端 token 里的 `domain` 字段也证实这点）。
- **从 localStorage / Cookies 里抠 JWT**：没有 `eyJ` 形态的浏览器令牌可用；桌面端
  Bearer 由客户端从本机 token 文件签发，agent 拿不到。但**直接读该 token 文件即可**（见上）。

## 安全护栏（重要）
- token 是敏感凭证：脚本只读不写、不打印、不落日志；本 skill 不存储它。
- 接口无「补签」能力，当天 0–24 点完全离线则错过（连签重置），任何工具都绕不过。
- 真实点击（兜底路径）会短暂抢前台约 3 秒，做完需归还前台与鼠标。

## 设为每日自动化（Windows 端）
用 `automation_update` 建 recurring（`FREQ=DAILY;BYHOUR=8;BYMINUTE=0`），prompt 用
Bash 跑 `claim_api.py`，按 stdout 的 `RESULT` 一句话汇报（成功静默 / 失败才展开）。

## 依赖
- **路径 A（推荐）**：纯 Python 标准库（urllib/json/os），Windows 用 WorkBuddy 托管
  Python、Mac 用 `/usr/bin/python3`，均无需额外安装。
- **路径 B（兜底）**：需 Pillow（仅 Windows UI 点击用）。
