#!/usr/bin/env python3
"""
10K Takes: Instagram follower collector (main account).

Reads the follower count of one Instagram Business/Creator account through
Meta's Graph API and saves a dated row to followers.csv:
    date,account,platform,followers

Needs two environment variables (stored as GitHub secrets):
  INSTAGRAM_ACCOUNT_ID  the numeric Instagram Business account ID
  FACEBOOK_PAGE_TOKEN   the Page access token (same one the Facebook script uses)

Uses only the Python standard library.
"""
import csv
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date

GRAPH_VERSION = "v26.0"
ACCOUNT_NAME = "10K Takes"
PLATFORM = "Instagram"
OUTPUT_FILE = "followers.csv"
HEADER = ["date", "account", "platform", "followers"]


def fetch_followers(ig_id, token):
    url = "https://graph.facebook.com/{}/{}?fields=username,followers_count".format(
        GRAPH_VERSION, ig_id)
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:400]
        sys.exit("Instagram API error {}: {}".format(e.code, body))
    except urllib.error.URLError as e:
        sys.exit("Could not reach Instagram: {}".format(e.reason))
    count = data.get("followers_count")
    if count is None:
        sys.exit("No follower count returned: {}".format(json.dumps(data)[:300]))
    return int(count), data.get("username", "")


def save_row(row):
    rows = []
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, newline="", encoding="utf-8") as f:
            rows = [r for r in csv.reader(f) if r and r != HEADER]
    rows = [r for r in rows if r[:3] != row[:3]]
    rows.append(row)
    rows.sort(key=lambda r: (r[0], r[1], r[2]))
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(rows)


def main():
    ig_id = os.environ.get("INSTAGRAM_ACCOUNT_ID", "").strip()
    token = os.environ.get("FACEBOOK_PAGE_TOKEN", "").strip()
    if not ig_id or not token:
        sys.exit("Set INSTAGRAM_ACCOUNT_ID and FACEBOOK_PAGE_TOKEN first.")
    count, username = fetch_followers(ig_id, token)
    today = date.today().isoformat()
    save_row([today, ACCOUNT_NAME, PLATFORM, str(count)])
    print("{} | {} | {} (@{}) | {:,}".format(today, ACCOUNT_NAME, PLATFORM, username, count))


if __name__ == "__main__":
    main()
