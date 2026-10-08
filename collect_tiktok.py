#!/usr/bin/env python3
"""
10K Takes: TikTok follower collector.

For each account below, trades its saved refresh token for a fresh access
token, reads the follower count, and saves a dated row to followers.csv:
    date,account,platform,followers

Environment variables (GitHub secrets):
  TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET
  one refresh-token variable per account (names in ACCOUNTS below)

It also records views and engagement in metrics.csv (date,account,platform,
metric,value) when the account was authorized with the video.list scope:
  views_7d         views so far on videos posted in the last 7 days
  engagements_7d   likes + comments + shares on those videos
Without that scope it quietly skips this part. Both jobs share ONE token
refresh per run, which matters because TikTok may rotate refresh tokens.

Accounts whose token variable is empty are skipped, so you can add accounts
one at a time. Uses only the Python standard library.
"""
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

ACCOUNTS = {
    "10K Takes": "TIKTOK_REFRESH_TOKEN_10K_TAKES",
    # "Wild Takes": "TIKTOK_REFRESH_TOKEN_WILD_TAKES",
    # "10K Howls": "TIKTOK_REFRESH_TOKEN_10K_HOWLS",
    # "State of Skol": "TIKTOK_REFRESH_TOKEN_STATE_OF_SKOL",
    # "The Underline": "TIKTOK_REFRESH_TOKEN_THE_UNDERLINE",
    # "Captain's Patch": "TIKTOK_REFRESH_TOKEN_CAPTAINS_PATCH",
}
PLATFORM = "TikTok"
OUTPUT_FILE = "followers.csv"
HEADER = ["date", "account", "platform", "followers"]
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
METRICS_FILE = "metrics.csv"
METRICS_HEADER = ["date", "account", "platform", "metric", "value"]
VIDEO_URL = "https://open.tiktokapis.com/v2/video/list/?fields=id,create_time,view_count,like_count,comment_count,share_count"
INFO_URL = "https://open.tiktokapis.com/v2/user/info/?fields=open_id,display_name,follower_count"


def http(req, label):
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError("{} error {}: {}".format(label, e.code, e.read().decode("utf-8", "replace")[:300]))
    except urllib.error.URLError as e:
        raise RuntimeError("{} unreachable: {}".format(label, e.reason))


def refresh(key, secret, refresh_token):
    body = urllib.parse.urlencode({
        "client_key": key, "client_secret": secret,
        "grant_type": "refresh_token", "refresh_token": refresh_token}).encode()
    req = urllib.request.Request(TOKEN_URL, data=body,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    data = http(req, "Token refresh")
    if "access_token" not in data:
        raise RuntimeError("Token refresh failed: {}".format(json.dumps(data)[:300]))
    return data


def followers(access_token):
    req = urllib.request.Request(INFO_URL, headers={"Authorization": "Bearer " + access_token})
    data = http(req, "User info")
    user = (data.get("data") or {}).get("user") or {}
    if "follower_count" not in user:
        raise RuntimeError("No follower_count returned (is user.info.stats granted?): {}".format(
            json.dumps(data)[:300]))
    return int(user["follower_count"]), user.get("display_name", "")


def week_metrics(access_token):
    """Views and engagement on videos created in the last 7 days (newest first)."""
    cutoff = time.time() - 7 * 86400
    views = engagements = cursor = pages = 0
    cursor = None
    while pages < 5:
        body = {"max_count": 20}
        if cursor:
            body["cursor"] = cursor
        req = urllib.request.Request(VIDEO_URL, data=json.dumps(body).encode(), headers={
            "Authorization": "Bearer " + access_token, "Content-Type": "application/json"})
        data = http(req, "Video list")
        err = (data.get("error") or {}).get("code", "ok")
        if err != "ok":
            raise RuntimeError("Video list: {}".format(json.dumps(data.get("error"))[:200]))
        page = data.get("data") or {}
        done = False
        for v in page.get("videos", []):
            if v.get("create_time", 0) < cutoff:
                done = True
                continue
            views += int(v.get("view_count", 0))
            engagements += sum(int(v.get(k, 0)) for k in ("like_count", "comment_count", "share_count"))
        pages += 1
        cursor = page.get("cursor")
        if done or not page.get("has_more"):
            break
    return views, engagements


def save_metric_rows(new_rows):
    rows = []
    if os.path.exists(METRICS_FILE):
        with open(METRICS_FILE, newline="", encoding="utf-8") as f:
            rows = [r for r in csv.reader(f) if r and r != METRICS_HEADER]
    keys = {tuple(r[:4]) for r in new_rows}
    rows = [r for r in rows if tuple(r[:4]) not in keys] + new_rows
    rows.sort(key=lambda r: (r[0], r[1], r[2], r[3]))
    with open(METRICS_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(METRICS_HEADER)
        w.writerows(rows)


def save_rows(new_rows):
    rows = []
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, newline="", encoding="utf-8") as f:
            rows = [r for r in csv.reader(f) if r and r != HEADER]
    keys = {tuple(r[:3]) for r in new_rows}
    rows = [r for r in rows if tuple(r[:3]) not in keys] + new_rows
    rows.sort(key=lambda r: (r[0], r[1], r[2]))
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(rows)


def main():
    key = os.environ.get("TIKTOK_CLIENT_KEY", "").strip()
    secret = os.environ.get("TIKTOK_CLIENT_SECRET", "").strip()
    if not key or not secret:
        sys.exit("Set TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET first.")
    today, new_rows, metric_rows, failed = date.today().isoformat(), [], [], []
    for account, var in ACCOUNTS.items():
        token = os.environ.get(var, "").strip()
        if not token:
            print("Skipping {} ({} is empty)".format(account, var))
            continue
        try:
            tok = refresh(key, secret, token)
            count, name = followers(tok["access_token"])
        except RuntimeError as e:
            failed.append(account)
            print("::error::{}: {}".format(account, e))
            continue
        new_rows.append([today, account, PLATFORM, str(count)])
        print("{} | {} | {} ({}) | {:,}".format(today, account, PLATFORM, name, count))
        try:
            views, engagements = week_metrics(tok["access_token"])
            metric_rows += [[today, account, PLATFORM, "views_7d", str(views)],
                            [today, account, PLATFORM, "engagements_7d", str(engagements)]]
            print("   last 7 days of videos: {:,} views, {:,} engagements".format(views, engagements))
        except RuntimeError as e:
            print("::notice::{} views/engagement skipped (needs the video.list scope): {}".format(account, e))
        new_token = tok.get("refresh_token")
        if new_token and new_token != token:
            print("::warning::TikTok issued a NEW refresh token for {}. Update the {} secret "
                  "with the new value before the old one stops working.".format(account, var))
    if new_rows:
        save_rows(new_rows)
    if metric_rows:
        save_metric_rows(metric_rows)
    if failed:
        sys.exit("Failed: " + ", ".join(failed))


if __name__ == "__main__":
    main()
