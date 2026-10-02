#!/usr/bin/env python3
"""
10K Takes: Facebook Page follower collector (main account).

Reads the follower count of one Facebook Page through Meta's Graph API and
saves a dated row to followers.csv:  date,account,platform,followers

Needs two environment variables (stored as GitHub secrets):
  FACEBOOK_PAGE_ID     the numeric ID of the Page
  FACEBOOK_PAGE_TOKEN  a Page access token for that Page

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
PLATFORM = "Facebook"
OUTPUT_FILE = "followers.csv"
HEADER = ["date", "account", "platform", "followers"]


def fetch_followers(page_id, token):
    url = "https://graph.facebook.com/{}/{}?fields=followers_count,fan_count".format(
        GRAPH_VERSION, page_id)
    # The token goes in a header, not the URL, so it can't leak into logs.
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:400]
        sys.exit("Facebook API error {}: {}".format(e.code, body))
    except urllib.error.URLError as e:
        sys.exit("Could not reach Facebook: {}".format(e.reason))
    count = data.get("followers_count")
    if count is None:
        count = data.get("fan_count")  # older field: page likes
    if count is None:
        sys.exit("Facebook returned no follower count: {}".format(json.dumps(data)[:300]))
    return int(count)


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
    page_id = os.environ.get("FACEBOOK_PAGE_ID", "").strip()
    token = os.environ.get("FACEBOOK_PAGE_TOKEN", "").strip()
    if not page_id or not token:
        sys.exit("Set FACEBOOK_PAGE_ID and FACEBOOK_PAGE_TOKEN first.")
    count = fetch_followers(page_id, token)
    today = date.today().isoformat()
    save_row([today, ACCOUNT_NAME, PLATFORM, str(count)])
    print("{} | {} | {} | {:,}".format(today, ACCOUNT_NAME, PLATFORM, count))


if __name__ == "__main__":
    main()
