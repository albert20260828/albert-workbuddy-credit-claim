# -*- coding: utf-8 -*-
"""Cross-platform WorkBuddy daily credit claim via the official API.

Reads the local desktop login token (written by the WorkBuddy / CodeBuddy
desktop client) and calls the official check-in endpoint. No UI automation,
works headless on both Windows and macOS.

Token file (same relative path on both OSes, different root):
  Windows: %LOCALAPPDATA%\\CodeBuddyExtension\\Data\\Public\\auth\\workbuddy-desktop.info
  macOS:   ~/Library/Application Support/CodeBuddyExtension/Data/Public/auth/workbuddy-desktop.info

Endpoint:
  POST https://<auth.domain>/v2/billing/meter/daily-checkin
  Authorization: <auth.tokenType> <auth.accessToken>

Exit codes (aligned with the macOS convention):
  0  success / already claimed today
  2  config error (token file missing / unreadable / no accessToken)
  3  network error (retries exhausted)
  4  auth failure (token expired -> open the client once to refresh)
  5  unexpected API response
"""
import json
import os
import sys
import urllib.request
import urllib.error

APP = "CodeBuddyExtension"
REL = os.path.join("Data", "Public", "auth", "workbuddy-desktop.info")


def token_path():
    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    elif sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA", "")
    elif sys.platform.startswith("linux"):
        base = os.path.expanduser("~/.local/share")  # desktop client is Win/Mac only
    else:
        base = ""
    if not base:
        return None
    return os.path.join(base, APP, REL)


def load_token(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
    except FileNotFoundError:
        return None, "token file not found: %s" % path
    except Exception as e:  # noqa: BLE001
        return None, "cannot read token file: %s" % e
    auth = d.get("auth") or {}
    access = auth.get("accessToken")
    ttype = auth.get("tokenType") or "Bearer"
    domain = auth.get("domain") or "www.codebuddy.cn"
    if not access:
        return None, "accessToken missing inside token file"
    return {"access": access, "type": ttype, "domain": domain}, None


def _call(token):
    url = "https://%s/v2/billing/meter/daily-checkin" % token["domain"]
    req = urllib.request.Request(
        url,
        data=b"{}",
        method="POST",
        headers={
            "Authorization": "%s %s" % (token["type"], token["access"]),
            "Content-Type": "application/json",
            "User-Agent": "albert-workbuddy-credit-claim",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.getcode(), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return -1, "network error: %s" % e


def claim(token):
    code, body = _call(token)
    try:
        j = json.loads(body)
    except Exception:  # noqa: BLE001
        j = {}
    msg = str(j.get("msg", ""))
    api_code = j.get("code")

    # The API signals status via the JSON `code` field, not the HTTP status:
    #   0      -> success
    #   10001  -> already claimed today (idempotent, safe to treat as success)
    if api_code in (0, 10001) or "成功" in msg or "已签到" in msg:
        return 0, body
    if code in (401, 403):
        return 4, body[:300]
    if code == -1:
        return 3, body
    return 5, "HTTP %s api_code=%s: %s" % (code, api_code, body[:300])


def main():
    dry = "--dry-run" in sys.argv
    path = token_path()
    if not path:
        print("RESULT: config_error (unsupported platform %s)" % sys.platform)
        return 2
    token, err = load_token(path)
    if not token:
        print("RESULT: config_error (%s)" % err)
        return 2
    if dry:
        print("DRY-RUN token_file=%s" % path)
        print("DRY-RUN would POST https://%s/v2/billing/meter/daily-checkin as %s <token len=%d>"
              % (token["domain"], token["type"], len(token["access"])))
        return 0
    code, detail = claim(token)
    print("RESULT: %s" % ("claimed" if code == 0 else "error_%d" % code))
    print(detail[:400])
    return code


if __name__ == "__main__":
    sys.exit(main())
