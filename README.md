# WorkBuddy 每日积分领取

自动领取 WorkBuddy 客户端「Buddy加油站·今日礼包」积分，解放双手，不再漏签。

---

## 功能特点

- 🖱️ **真实点击**：截图定位左下角卡牌的「立即领取」黑色按钮，用**真实鼠标点击**完成领取（Chromium 会丢弃合成消息，必须真实点击）
- 🛡️ **安全护栏**：点击前先用 `WindowFromPoint` 校验落点确实归属 WorkBuddy 进程，**绝不误点**前台其它窗口
- 🔁 **抗抢占重试**：前台有全屏游戏夹住鼠标时自动重切前台、释放 `ClipCursor`，最多重试 30 次，落点不到位就绝不盲点
- ⏰ **每日定时**：内置每日 08:00 自动领取的自动化配置，可脱离人工长期运行
- ↩️ **无感执行**：完成后自动归还鼠标位置、`ClipCursor` 与原前台窗口，抢前台约 3 秒
- 📋 **结果可判**：stdout 输出 `RESULT` 状态码，便于自动化流程判断成功 / 已领 / 失败
- 🧹 **不脏目录**：调试截图写在 `%TEMP%/wb-credit-claim/`，不污染 skill 自身

---

## 快速开始

### 前提条件

- **仅 Windows**（依赖 `user32` / `gdi32` 的 `ctypes` 与 `PrintWindow`）
- **Python 3.x + Pillow**（建议装在 WorkBuddy 托管的 venv 里）
- **WorkBuddy 客户端已安装并处于运行状态**（领取动作发生在客户端窗口内）
- 屏幕分辨率建议 1920×1080 或更高（按钮定位基于比例坐标，低分屏可能偏移）

### 方案：Python ctypes（唯一实现）

`scripts/claim_daily.py` 是自包含的生产脚本，无需前台、不被遮挡即可截取窗口：

```bash
"<managed-python>" "<skill>\scripts\claim_daily.py"
```

> 说明：本 skill 只提供 Python ctypes 一种实现。不提供 PowerShell / Playwright 版本的原因见文末「为什么这样做」——PostMessage 合成输入会被 Chromium 丢弃，UIAutomation 树为空，都不是可行路径。

### 设为每日自动化

在 WorkBuddy 里建一条每日定时任务（每天 08:00）：

- **rrule**：`FREQ=DAILY;BYHOUR=8;BYMINUTE=0`
- **prompt**：用 Bash 跑上面的脚本，并按 stdout 的 `RESULT` 一句话汇报（成功静默 / 失败才展开说明）

---

## RESULT 输出说明

| RESULT | 含义 | 建议处理 |
| --- | --- | --- |
| `claimed` | 按钮消失，领取成功 | 回一句「今日积分已领 ✓」 |
| `button_not_found` | 今天已领过 / 卡牌未显示 | 正常，**不要重试** |
| `click_no_effect` | 点击后按钮仍在 | 看 `after.png` 确认后重试一次，仍失败则明说失败 |
| `no_window` | 未找到 WorkBuddy 窗口 | 说明原因，确认客户端在运行 |
| `window_hidden_in_tray` | 窗口在托盘且唤不醒 | 说明原因，需手动打开客户端 |
| `cursor_move_blocked` | 鼠标被夹住，落点不到位 | 前台可能被全屏程序占用，说明原因，不盲点 |
| `point_occluded` | 落点被其它窗口遮挡 | 说明原因，不盲点 |

---

## 目录结构

```
albert-workbuddy-credit-claim/
├── SKILL.md               # 技能说明与调用约定
├── README.md              # 本文件（简介）
├── scripts/
│   └── claim_daily.py     # 自包含领取脚本
└── references/
    └── workflow.md        # 完整工作流、接口勘察与死路清单
```

---

## 为什么这样做（避坑要点）

- **不走后端 API**：接口确实存在（`/billing/meter/daily-checkin` 等），但桌面端 Bearer token 存在主进程加密存储，本地拿不到可用的 JWT；Web 端又需另行登录。故改为 UI 真实点击。
- **不用 UIAutomation**：Electron 未开启可访问性支持，无障碍树为空（`FindAll(Descendants)` 只返回 1 个元素）；要开启必须加启动参数重启，会杀掉当前会话。
- **不用 PostMessage**：投递给 Chromium 的合成鼠标消息一律被过滤丢弃。
- **必须校验与还原**：真实点击会短暂抢前台，且若前台是全屏游戏可能把鼠标夹住——所以点击前校验归属、点击后还原焦点/鼠标，被夹住就重试而非盲点。

> 详细勘察过程与全部走不通的尝试，见 `references/workflow.md`。
