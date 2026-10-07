#!/usr/bin/env python3
"""
10K Takes: YouTube views and engagement collector (main channel).

Writes to metrics.csv:  date,account,platform,metric,value
  views_total / engagements_total   running totals (used as a baseline)
  views_7d / engagements_7d         growth over the last 7 days (what the
                                    dashboard shows); appears once a baseline
                                    7 days old exists

Engagements = likes + comments across the channel's latest uploads.
Uses the same YOUTUBE_API_KEY secret as collect_youtube.py. Standard library only.
"""
import csv
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

HANDLE = "@10K_Takes"
ACCOUNT = "10K Takes"
PLATFORM = "YouTube"
MAX_VIDEOS = 200
OUT = "metrics.csv"
HEADER = ["date", "account", "platform", "metric", "value"]
BASE = "https://www.googleapis.com/youtube/v3/"


def api(path, params, key):
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"X-Goog-Api-Key": key})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit("YouTube API error {}: {}".format(e.code, e.read().decode("utf-8", "replace")[:300]))
    except urllib.error.URLError as e:
        sys.exit("Could not reach YouTube: {}".format(e.reason))


def read_rows():
    if not os.path.exists(OUT):
        return []
    with open(OUT, newline="", encoding="utf-8") as f:
        return [r for r in csv.reader(f) if r and r != HEADER]


def write_rows(rows):
    rows.sort(key=lambda r: (r[0], r[1], r[2], r[3]))
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(rows)


def baseline(rows, metric, target):
    """Latest stored value on or before target, but no more than 3 days older."""
    best = None
    for r in rows:
        if r[1] == ACCOUNT and r[2] == PLATFORM and r[3] == metric:
            d = date.fromisoformat(r[0])
            if target - timedelta(days=3) <= d <= target and (best is None or d > best[0]):
                best = (d, int(r[4]))
    return best[1] if best else None


def main():
    key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not key:
        sys.exit("Set the YOUTUBE_API_KEY environment variable first.")
    ch = api("channels", {"part": "statistics,contentDetails", "forHandle": HANDLE}, key)
    items = ch.get("items") or []
    if not items:
        sys.exit("No channel found for " + HANDLE)
    views_total = int(items[0]["statistics"]["viewCount"])
    uploads = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    ids, token = [], None
    while len(ids) < MAX_VIDEOS:
        p = {"part": "contentDetails", "playlistId": uploads, "maxResults": 50}
        if token:
            p["pageToken"] = token
        page = api("playlistItems", p, key)
        ids += [i["contentDetails"]["videoId"] for i in page.get("items", [])]
        token = page.get("nextPageToken")
        if not token:
            break
    ids = ids[:MAX_VIDEOS]

    eng_total = 0
    for i in range(0, len(ids), 50):
        v = api("videos", {"part": "statistics", "id": ",".join(ids[i:i + 50])}, key)
        for item in v.get("items", []):
            s = item.get("statistics", {})
            eng_total += int(s.get("likeCount", 0)) + int(s.get("commentCount", 0))

    today = date.today()
    rows = read_rows()
    new = [("views_total", views_total), ("engagements_total", eng_total)]
    for name, total in (("views", views_total), ("engagements", eng_total)):
        base = baseline(rows, name + "_total", today - timedelta(days=7))
        if base is not None:
            new.append((name + "_7d", max(0, total - base)))
    keys = {m for m, _ in new}
    rows = [r for r in rows if not (r[0] == today.isoformat() and r[1] == ACCOUNT
                                    and r[2] == PLATFORM and r[3] in keys)]
    for m, val in new:
        rows.append([today.isoformat(), ACCOUNT, PLATFORM, m, str(val)])
    write_rows(rows)
    print("{} | {} | {} | {}".format(today, ACCOUNT, PLATFORM,
                                     ", ".join("{}={:,}".format(m, v) for m, v in new)))
    if len(new) == 2:
        print("No 7-day baseline yet. Weekly numbers start appearing after a week of daily runs.")


if __name__ == "__main__":
    main()
