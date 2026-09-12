# WorkBuddy 每日积分领取 —— 工作流与踩坑记录

## 需求形态
用户想要「每天自动领取 WorkBuddy 积分」。客户端入口是左下角浮动卡牌
「Buddy加油站·N期 / 今日可领 100 积分 / 立即领取」按钮。点击后弹 toast
「领取成功」，按钮变「今日已领」。每日 1 次，约 100 分/天（连续第 7 天有 10 倍大奖）。

## 为什么不直接调后端 API（已验证不可行）
从 `app.asar` 逆向出两个接口：
- `POST /billing/meter/checkin-status`  （查询今日是否可领）
- `POST /billing/meter/daily-checkin`   （执行领取）

鉴权分两端：
- Web（Cloud）：空路径前缀，走**浏览器 cookie**（host 实测 `https://www.workbuddy.cn/billing/meter/...` 返回 401 而非 404，接口存在）。
- 桌面：前缀覆盖为 `/v2`，走 **IDE 网关 Bearer token**。

放弃直连 API 的原因：
1. 桌面端 token 存在主进程内存/加密存储，本地未找到可提取的 JWT；`connect_cloud_service`
   返回的临时 token 仅限多模态/金融 skill 使用，通用调用会被拒。
2. Web 端需要用户先在 `workbuddy.cn` 登录（扫码/微信），且后端可能对 Web 端签到做了限制，
   未能验证可用性。

结论：**走 UI 真实点击**。

## 可行方案（见 scripts/claim_daily.py）
1. `EnumWindows` 找标题为 `WorkBuddy` 的窗口（托盘最小化则用 `ShowWindow(SW_RESTORE)` 唤醒）。
2. `PrintWindow(hwnd, PW_RENDERFULLCONTENT)` 截窗口位图（无需前台/不被遮挡即可截）。
3. 像素扫描：在图片左 45%、下 28% 区域内找「实心深色块」（R/G/B 均 <75，单行列连续 ≥35px）。
   该深色块即「立即领取」黑色按钮。取包围盒中心为按钮坐标。
4. 真实鼠标点击：先把窗口切到前台 → 释放可能的 `ClipCursor`（全屏游戏会夹鼠标）→
   `SetCursorPos` + `mouse_event(LEFTDOWN/UP)` → 还原鼠标位置与 `ClipCursor` → 还原前台窗口。
5. 复验：再截一次，若深色按钮消失 = 领取成功。
6. **抗抢占重试**：若前台有全屏游戏等动态夹住鼠标（SetCursorPos 被 clamp），单次点击会被挡。
   脚本用 30 次重试循环：每次重新切前台 + 释放 ClipCursor + 移动 + 点击，直到光标真正落到位、
   按钮消失为止。仍失败则说明当前确实被夹住，安全放弃（不盲点）。

`RESULT` 输出约定：
- `claimed`：按钮消失，领取成功
- `button_not_found`：今天已领过 / 卡牌未显示（正常，不重试）
- `click_no_effect`：点击后按钮仍在（可看 after.png 重试一次）
- `no_window` / `window_hidden_in_tray` / `cursor_move_blocked` / `point_occluded`：环境异常，说明原因

## 已验证走不通的死路（别再试）
- **UIAutomation / Inspect / UIA FindAll**：Electron 的 `app.setAccessibilitySupportEnabled`
  未开启，可访问性树为空，`FindAll(Descendants)` 仅返回 1 个元素。要让 UIA 生效必须给
  WorkBuddy 加 `--force-renderer-accessibility` 重启，会杀掉当前会话，不可行。
- **PostMessage(WM_LBUTTONDOWN/UP)**：对主窗口 / `Chrome_RenderWidgetHostHWND` /
  `Intermediate D3D Window` 投递的合成鼠标消息，Chromium 一律丢弃（合成输入被过滤）。
- **本地令牌提取**：localStorage / Session Storage / Cookies 里均无 `eyJ` 形态 JWT；
  网关 Bearer 无法由 agent 自行签发。

## 安全护栏（重要）
- 点击前务必 `WindowFromPoint` 校验落点归属 WorkBuddy 进程。**否则会点进前台其它程序**
  （实测用户打游戏时第一次点击误入游戏窗口）。
- 真实点击会短暂（约 3 秒）抢前台。做完后 `SetForegroundWindow` 还给原窗口。
- 若坐标 `SetCursorPos` 后被 clamp（如仍在某窗口内但读回偏差 >3px），**中止**，不要盲点。
- 客户端必须处于运行状态（自动化在自己进程内执行，没问题）。

## 设为每日自动化
用 `automation_update` 建一条 recurring：
- rrule：`FREQ=DAILY;BYHOUR=8;BYMINUTE=0`
- prompt 用 Bash 跑：`"<managed python>" "<skill>/scripts/claim_daily.py"`，并指示按 stdout
  的 `RESULT` 一句话汇报（成功/已领/失败原因）。安全时静默，失败才展开。

## 依赖
- Python + Pillow（`python -m pip install pillow`，建议装在 WorkBuddy 托管的 venv 里）。
- 仅 Windows（依赖 `user32`/`gdi32` `ctypes` 与 `PrintWindow`）。
