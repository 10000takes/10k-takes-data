#!/usr/bin/env python3
"""
10K Takes: X/Twitter views and engagement collector (main account).

Reads the posts the account published in the last 7 days and saves two rows
to metrics.csv (date,account,platform,metric,value):
  views_7d         impressions so far on posts published in the last 7 days
  engagements_7d   likes + replies + reposts + quotes on those posts

Note: this is "performance of the last 7 days of posts", so it undercounts
late views on older posts. Use it for trends, not for exact comparison with
other platforms.

Uses X_BEARER_TOKEN (same secret as the follower script). Costs credits per
post read (roughly half a cent each), so MAX_POSTS caps the daily spend.
Standard library only.
"""
import csv
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

HANDLE = "10K_Takes"
ACCOUNT = "10K Takes"
PLATFORM = "X/Twitter"
MAX_POSTS = 100
OUT = "metrics.csv"
HEADER = ["date", "account", "platform", "metric", "value"]
BASE = "https://api.x.com/2/"


def api(path, params, token):
    url = BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        hint = " (402 usually means the account is out of credits)" if e.code == 402 else ""
        sys.exit("X API error {}{}: {}".format(e.code, hint, e.read().decode("utf-8", "replace")[:300]))
    except urllib.error.URLError as e:
        sys.exit("Could not reach X: {}".format(e.reason))


def save(new_rows):
    rows = []
    if os.path.exists(OUT):
        with open(OUT, newline="", encoding="utf-8") as f:
            rows = [r for r in csv.reader(f) if r and r != HEADER]
    keys = {tuple(r[:4]) for r in new_rows}
    rows = [r for r in rows if tuple(r[:4]) not in keys] + new_rows
    rows.sort(key=lambda r: (r[0], r[1], r[2], r[3]))
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(rows)


def main():
    token = os.environ.get("X_BEARER_TOKEN", "").strip()
    if not token:
        sys.exit("Set the X_BEARER_TOKEN environment variable first.")
    user = api("users/by/username/" + HANDLE, {}, token)
    if "data" not in user:
        sys.exit("User not found: " + json.dumps(user)[:200])
    uid = user["data"]["id"]

    start = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    posts, nxt = [], None
    while len(posts) < MAX_POSTS:
        p = {"max_results": min(100, max(5, MAX_POSTS - len(posts))), "start_time": start,
             "exclude": "retweets", "tweet.fields": "public_metrics,created_at"}
        if nxt:
            p["pagination_token"] = nxt
        page = api("users/{}/tweets".format(uid), p, token)
        posts += page.get("data", [])
        nxt = (page.get("meta") or {}).get("next_token")
        if not nxt:
            break
    posts = posts[:MAX_POSTS]

    views = engagements = 0
    missing = 0
    for post in posts:
        m = post.get("public_metrics", {})
        if "impression_count" not in m:
            missing += 1
        views += int(m.get("impression_count", 0))
        engagements += sum(int(m.get(k, 0)) for k in
                           ("like_count", "reply_count", "retweet_count", "quote_count"))
    if posts and missing == len(posts):
        sys.exit("X did not return impression_count for these posts, so views cannot be saved.")

    today = date.today().isoformat()
    save([[today, ACCOUNT, PLATFORM, "views_7d", str(views)],
          [today, ACCOUNT, PLATFORM, "engagements_7d", str(engagements)]])
    print("{} | {} | {} | {} posts | views_7d={:,} engagements_7d={:,}".format(
        today, ACCOUNT, PLATFORM, len(posts), views, engagements))


if __name__ == "__main__":
    main()
