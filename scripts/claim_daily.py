# -*- coding: utf-8 -*-
"""WorkBuddy daily credit claim (Buddy加油站·今日礼包 check-in).

Approach: screenshot the client window with PrintWindow, locate the solid dark
"立即领取" button by pixel analysis, bring the window to the foreground briefly,
perform a REAL mouse click (Chromium drops synthetic input), verify, then restore
focus and cursor. UIAutomation and PostMessage are explicitly NOT used — see the
skill's references/workflow.md for why.
"""
import ctypes
import ctypes.wintypes as wt
import os
import sys
import tempfile
import time

from PIL import Image

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
gdi32 = ctypes.windll.gdi32

try:
    user32.SetProcessDPIAware()
except Exception:
    pass

# Debug screenshots go to a temp dir (not next to the script) so the skill stays clean.
OUT_DIR = os.path.join(tempfile.gettempdir(), "wb-credit-claim")
os.makedirs(OUT_DIR, exist_ok=True)
WINDOW_TITLE = "WorkBuddy"
PW_RENDERFULLCONTENT = 0x00000002


def find_main_window():
    result = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    def cb(hwnd, lparam):
        n = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        if buf.value == WINDOW_TITLE:
            result.append(hwnd)
        return True

    user32.EnumWindows(cb, 0)
    for h in result:                      # prefer a visible window
        if user32.IsWindowVisible(h):
            return h
    return result[0] if result else None


def capture(hwnd):
    class BMIH(ctypes.Structure):
        _fields_ = [("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32),
                    ("biHeight", ctypes.c_int32), ("biPlanes", ctypes.c_uint16),
                    ("biBitCount", ctypes.c_uint16), ("biCompression", ctypes.c_uint32),
                    ("biSizeImage", ctypes.c_uint32), ("biXPelsPerMeter", ctypes.c_int32),
                    ("biYPelsPerMeter", ctypes.c_int32), ("biClrUsed", ctypes.c_uint32),
                    ("biClrImportant", ctypes.c_uint32)]
    rect = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w, h = rect.right - rect.left, rect.bottom - rect.top
    hdc = user32.GetWindowDC(hwnd)
    mem = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mem, bmp)
    user32.PrintWindow(hwnd, mem, PW_RENDERFULLCONTENT)
    bi = BMIH()
    bi.biSize = ctypes.sizeof(BMIH)
    bi.biWidth, bi.biHeight, bi.biPlanes, bi.biBitCount = w, -h, 1, 32
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(bi), 0)
    img = Image.frombuffer("RGBA", (w, h), buf.raw, "raw", "BGRA", 0, 1).convert("RGB")
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mem)
    user32.ReleaseDC(hwnd, hdc)
    return img, (rect.left, rect.top, rect.right, rect.bottom)


def find_button(img):
    """Locate the solid dark claim button inside the bottom-left gift card."""
    w, h = img.size
    px = img.load()
    hits = []
    for y in range(int(h * 0.72), h):
        run = s = mx = ms = me = 0
        for x in range(0, int(w * 0.45)):
            r, g, b = px[x, y]
            if r < 75 and g < 75 and b < 75:
                if run == 0:
                    s = x
                run += 1
                if run > mx:
                    mx, ms, me = run, s, x
            else:
                run = 0
        if mx >= 35:
            hits.append((ms, me, y))
    if len(hits) < 5:
        return None
    xs = [p[0] for p in hits] + [p[1] for p in hits]
    ys = [p[2] for p in hits]
    bw, bh = max(xs) - min(xs), max(ys) - min(ys)
    if not (35 <= bw <= 200 and 12 <= bh <= 60):
        return None
    return ((min(xs) + max(xs)) // 2, (min(ys) + max(ys)) // 2)


def window_thread(hwnd):
    return user32.GetWindowThreadProcessId(hwnd, None)


def hwnd_pid(hwnd):
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def force_foreground(hwnd):
    fg = user32.GetForegroundWindow()
    me = kernel32.GetCurrentThreadId()
    t_fg = window_thread(fg)
    t_wd = window_thread(hwnd)
    user32.AttachThreadInput(me, t_fg, True)
    user32.AttachThreadInput(me, t_wd, True)
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)
    user32.AttachThreadInput(me, t_fg, False)
    user32.AttachThreadInput(me, t_wd, False)
    time.sleep(0.4)
    return user32.GetForegroundWindow() == hwnd


def main():
    hwnd = find_main_window()
    if not hwnd:
        print("RESULT: no_window")
        return 1
    if (not user32.IsWindowVisible(hwnd)) or user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)            # SW_RESTORE
        time.sleep(1.5)
        if not user32.IsWindowVisible(hwnd):
            print("RESULT: window_hidden_in_tray")
            return 1

    img, rect = capture(hwnd)
    img.save(os.path.join(OUT_DIR, "before.png"))
    btn = find_button(img)
    if btn is None:
        # Card gone / already claimed / button text changed to "今日已领"
        print("RESULT: button_not_found (likely already claimed today)")
        return 0
    bx, by = btn
    sx, sy = rect[0] + bx, rect[1] + by
    print("button window(%d,%d) -> screen(%d,%d)" % (bx, by, sx, sy))

    prev_fg = user32.GetForegroundWindow()
    clip = wt.RECT()
    user32.GetClipCursor(ctypes.byref(clip))
    pt = wt.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    old_cursor = (pt.x, pt.y)

    # Retry loop: a foreground fullscreen app (e.g. a game) may dynamically re-clip
    # the cursor, so a single attempt can be clamped. Re-steal focus, release the
    # clip, move, and click until the cursor actually lands and the button disappears.
    claimed = False
    for _ in range(30):
        force_foreground(hwnd)
        user32.ClipCursor(None)
        time.sleep(0.05)
        user32.SetCursorPos(sx, sy)
        time.sleep(0.04)
        user32.GetCursorPos(ctypes.byref(pt))
        if abs(pt.x - sx) > 3 or abs(pt.y - sy) > 3:
            continue                       # cursor still clamped -> retry
        hit = user32.WindowFromPoint(wt.POINT(sx, sy))
        if hwnd_pid(hit) != hwnd_pid(hwnd):
            continue                       # not on WorkBuddy -> retry
        user32.mouse_event(0x0002, 0, 0, 0, 0)   # left down
        time.sleep(0.06)
        user32.mouse_event(0x0004, 0, 0, 0, 0)   # left up
        time.sleep(0.4)
        img2, _ = capture(hwnd)
        if find_button(img2) is None:
            img2.save(os.path.join(OUT_DIR, "after.png"))
            claimed = True
            break

    user32.SetCursorPos(old_cursor[0], old_cursor[1])
    user32.ClipCursor(ctypes.byref(clip))
    if prev_fg and prev_fg != hwnd:
        user32.SetForegroundWindow(prev_fg)
    if claimed:
        print("RESULT: claimed")
    else:
        imgf, _ = capture(hwnd)
        print("RESULT: button_not_found (likely already claimed)"
              if find_button(imgf) is None else "RESULT: click_no_effect")
    return 0


if __name__ == "__main__":
    sys.exit(main())
