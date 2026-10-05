#!/usr/bin/env python3
"""
One-time TikTok authorization helper. Run on YOUR computer, not in GitHub.

Environment variables to set first:
  TIKTOK_CLIENT_KEY      from your TikTok developer app
  TIKTOK_CLIENT_SECRET   from your TikTok developer app (keep private)
  TIKTOK_REDIRECT_URI    the exact callback address registered in the app

Step 1:  python3 tiktok_setup.py url
         Open the printed link while logged in to the TikTok account, approve,
         and copy the code shown on the callback page.
Step 2:  python3 tiktok_setup.py exchange "THE_CODE"
         Prints the refresh token to store as a GitHub secret.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

SCOPES = "user.info.basic,user.info.stats"


def env(name):
    v = os.environ.get(name, "").strip()
    if not v:
        sys.exit("Set the {} environment variable first.".format(name))
    return v


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("url", "exchange"):
        sys.exit(__doc__)
    key, redirect = env("TIKTOK_CLIENT_KEY"), env("TIKTOK_REDIRECT_URI")
    if sys.argv[1] == "url":
        print("https://www.tiktok.com/v2/auth/authorize/?" + urllib.parse.urlencode({
            "client_key": key, "scope": SCOPES, "response_type": "code",
            "redirect_uri": redirect, "state": "10ktakes"}))
        return
    if len(sys.argv) < 3:
        sys.exit('Usage: python3 tiktok_setup.py exchange "THE_CODE"')
    body = urllib.parse.urlencode({
        "client_key": key, "client_secret": env("TIKTOK_CLIENT_SECRET"),
        "code": sys.argv[2].strip(), "grant_type": "authorization_code",
        "redirect_uri": redirect}).encode()
    req = urllib.request.Request("https://open.tiktokapis.com/v2/oauth/token/", data=body,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit("TikTok error {}: {}".format(e.code, e.read().decode("utf-8", "replace")[:400]))
    if "refresh_token" not in data:
        sys.exit("Unexpected response: {}".format(json.dumps(data)[:400]))
    print("Granted scopes:", data.get("scope"))
    if "user.info.stats" not in (data.get("scope") or ""):
        print("WARNING: user.info.stats was not granted, so follower counts will not work.")
    print("\nREFRESH TOKEN (save as a GitHub secret, never share it):\n")
    print(data["refresh_token"])


if __name__ == "__main__":
    main()
