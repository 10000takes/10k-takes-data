#!/usr/bin/env python3
"""
Threads token helper. Run on YOUR computer, not in GitHub.

  python3 threads_setup.py exchange 'SHORT_LIVED_TOKEN'
      Swaps the 1-hour token from the Threads token generator for a 60-day
      token. Needs THREADS_APP_SECRET set (the Threads app secret, not the
      Facebook app secret).

  python3 threads_setup.py refresh 'LONG_LIVED_TOKEN'
      Extends a still-valid 60-day token for another 60 days. The token must
      be at least 24 hours old. Do this about every 50 days.

Always wrap the token in SINGLE quotes. Prints the new token; save it as the
GitHub secret for that account. Never share it.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def get(url, params, secrets):
    full = url + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(full, timeout=20) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:400]
        for s in secrets:
            body = body.replace(s, "***")
        sys.exit("Threads error {}: {}".format(e.code, body))


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("exchange", "refresh"):
        sys.exit(__doc__)
    token = sys.argv[2].strip()
    if sys.argv[1] == "exchange":
        secret = os.environ.get("THREADS_APP_SECRET", "").strip()
        if not secret:
            sys.exit("Set THREADS_APP_SECRET first.")
        data = get("https://graph.threads.net/access_token",
                   {"grant_type": "th_exchange_token", "client_secret": secret,
                    "access_token": token}, [token, secret])
    else:
        data = get("https://graph.threads.net/refresh_access_token",
                   {"grant_type": "th_refresh_token", "access_token": token}, [token])
    if "access_token" not in data:
        sys.exit("Unexpected response: " + json.dumps(data)[:300])
    days = int(data.get("expires_in", 0)) // 86400
    print("Valid for about {} days.\n\nTOKEN (save as a GitHub secret, never share):\n".format(days))
    print(data["access_token"])


if __name__ == "__main__":
    main()
