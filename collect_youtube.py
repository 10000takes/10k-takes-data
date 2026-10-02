#!/usr/bin/env python3
"""
10K Takes: YouTube follower collector.

Reads the public subscriber count for the main channel and saves one dated row
to followers.csv in the format the dashboard imports:
    date,account,platform,followers

Setup:
  1. Put your API key in an environment variable named YOUTUBE_API_KEY.
       Mac/Linux:  export YOUTUBE_API_KEY="your-key"
       Windows:    setx YOUTUBE_API_KEY "your-key"   (then reopen the terminal)
  2. Set CHANNEL_HANDLE below to your channel's handle.
  3. Run:  python3 collect_youtube.py

Uses only the Python standard library (Python 3.8+). Nothing to install.

Note: the public YouTube API rounds subscriber counts to three significant
digits (48,210 is reported as 48,200). Weekly gains will be approximate.
"""
import csv
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

CHANNEL_HANDLE = "@10K_Takes"
ACCOUNT_NAME = "10K Takes"     # must match the dashboard's account name
PLATFORM = "YouTube"
OUTPUT_FILE = "followers.csv"
HEADER = ["date", "account", "platform", "followers"]


def fetch_subscribers(handle, api_key):
    params = urllib.parse.urlencode({
        "part": "statistics",
        "forHandle": handle,
        "key": api_key,
    })
    url = "https://www.googleapis.com/youtube/v3/channels?" + params
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        # Print the status only, never the URL, so the key is not leaked in logs.
        body = e.read().decode("utf-8", "replace")[:300]
        sys.exit("YouTube API error {}: {}".format(e.code, body))
    except urllib.error.URLError as e:
        sys.exit("Could not reach YouTube: {}".format(e.reason))

    items = data.get("items") or []
    if not items:
        sys.exit("No channel found for handle {}. Check the spelling.".format(handle))
    stats = items[0]["statistics"]
    if stats.get("hiddenSubscriberCount"):
        sys.exit("This channel hides its subscriber count, so it can't be read.")
    return int(stats["subscriberCount"])


def save_row(row):
    rows = []
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, newline="", encoding="utf-8") as f:
            rows = [r for r in csv.reader(f) if r and r != HEADER]
    # Replace any existing row for the same date, account and platform.
    rows = [r for r in rows if r[:3] != row[:3]]
    rows.append(row)
    rows.sort(key=lambda r: (r[0], r[1], r[2]))
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(rows)


def main():
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        sys.exit("Set the YOUTUBE_API_KEY environment variable first.")
    count = fetch_subscribers(CHANNEL_HANDLE, api_key)
    today = date.today().isoformat()
    save_row([today, ACCOUNT_NAME, PLATFORM, str(count)])
    print("{} | {} | {} | {:,}".format(today, ACCOUNT_NAME, PLATFORM, count))
    print("Saved to " + OUTPUT_FILE)


if __name__ == "__main__":
    main()
