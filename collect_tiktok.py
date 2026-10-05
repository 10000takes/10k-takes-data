#!/usr/bin/env python3
"""
10K Takes: TikTok follower collector.

For each account below, trades its saved refresh token for a fresh access
token, reads the follower count, and saves a dated row to followers.csv:
    date,account,platform,followers

Environment variables (GitHub secrets):
  TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET
  one refresh-token variable per account (names in ACCOUNTS below)

Accounts whose token variable is empty are skipped, so you can add accounts
one at a time. Uses only the Python standard library.
"""
import csv
import json
import os
import sys
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
    today, new_rows, failed = date.today().isoformat(), [], []
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
        new_token = tok.get("refresh_token")
        if new_token and new_token != token:
            print("::warning::TikTok issued a NEW refresh token for {}. Update the {} secret "
                  "with the new value before the old one stops working.".format(account, var))
    if new_rows:
        save_rows(new_rows)
    if failed:
        sys.exit("Failed: " + ", ".join(failed))


if __name__ == "__main__":
    main()
