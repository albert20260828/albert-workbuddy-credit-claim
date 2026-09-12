---
name: albert-workbuddy-credit-claim
description: "Use this skill when the user asks to automatically claim WorkBuddy daily check-in credits (the Buddy加油站·今日礼包 / 立即领取 button), set up a recurring daily automation for it, or build UI automation that clicks a button inside the WorkBuddy desktop client. Documents the only working approach (screenshot pixel-locate plus real mouse click) and the dead-ends that must be avoided (UIAutomation empty tree, PostMessage ignored by Chromium, local token extraction)."
agent_created: true
---

# WorkBuddy 每日积分领取

## Overview

Automatically claim the WorkBuddy client's daily check-in credits ("Buddy加油站·今日礼包"
floating card → "立即领取" button). The skill bundles a production-ready Windows script
that locates the button from a screenshot, performs a real foreground mouse click, verifies
the result, and restores focus/cursor. It also records the investigation dead-ends so future
runs do not waste effort re-deriving them.

## When to use

- User says "每天自动领取积分 / 自动签到 / 领 WorkBuddy 积分 / 领 Buddy加油站".
- User wants a daily recurring automation inside WorkBuddy (runs at a scheduled time).
- User asks to click any button inside the WorkBuddy desktop client programmatically.

## How to use

1. Run `scripts/claim_daily.py` with the WorkBuddy-managed Python (Pillow required):
   put the managed-python executable and the skill's scripts/claim_daily.py path as the two args.
2. Interpret stdout `RESULT`:
   - `claimed` → success.
   - `button_not_found` → already claimed today / card not shown (normal, do **not** retry).
   - `click_no_effect` → check the skill's after.png, retry once.
   - `no_window` / `window_hidden_in_tray` / `cursor_move_blocked` / `point_occluded` →
     report the reason; do not loop.
3. To schedule daily, create a recurring automation (`FREQ=DAILY;BYHOUR=8;BYMINUTE=0`) whose
   prompt runs the script and replies in one sentence (silent on success, explain on failure).

## Critical constraints (read before any rewrite)

- **Use a real mouse click, never PostMessage/UIAutomation.** Chromium drops synthetic
  input and the Electron a11y tree is empty. See `references/workflow.md` for the full
  evidence.
- **Verify the click target with `WindowFromPoint` first.** If another window (e.g. a game)
  is on top, clicking blindly hits that window instead.
- **Restore focus and cursor afterward.** The real click briefly steals the foreground
  (~3s); restore the previous foreground window and original cursor position + `ClipCursor`.
- Windows-only; depends on `user32`/`gdi32` via `ctypes` and `PrintWindow`.
- The client must be running for the claim (and for an in-client automation) to work.

## Resources

### scripts/
- `claim_daily.py` — self-contained claimer: find window → `PrintWindow` screenshot →
  pixel-locate the dark "立即领取" button → real click → re-screenshot to verify → restore
  state. Writes `before.png` / `after.png` next to itself for debugging.

### references/
- `workflow.md` — full workflow, the discovered backend endpoints (and why direct API was
  abandoned), and the exhaustive list of approaches that do **not** work.
