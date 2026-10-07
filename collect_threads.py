#!/usr/bin/env python3
"""
10K Takes: Threads follower collector.
 
For each account below, reads the follower count through the Threads Insights
API and saves a dated row to followers.csv:  date,account,platform,followers
 
It also records views and engagement for the last 7 days in metrics.csv
(date,account,platform,metric,value) for the dashboard's performance section.
Engagements = likes + replies + reposts + quotes.
 
Each account needs a long-lived Threads access token stored as a GitHub secret
(variable names in ACCOUNTS). Accounts whose variable is empty are skipped, so
you can add them one at a time. Tokens last 60 days: refresh them with
threads_setup.py about every 50 days.
 
Uses only the Python standard library.
"""
import csv
import json
import os
import sys
import urllib.error
import urllib.parse
import time
import urllib.request
from datetime import date
 
ACCOUNTS = {
    "10K Takes": "THREADS_ACCESS_TOKEN_10K_TAKES",
    # "Wild Takes": "THREADS_ACCESS_TOKEN_WILD_TAKES",
    # "10K Howls": "THREADS_ACCESS_TOKEN_10K_HOWLS",
    # "State of Skol": "THREADS_ACCESS_TOKEN_STATE_OF_SKOL",
    # "The Underline": "THREADS_ACCESS_TOKEN_THE_UNDERLINE",
    # "Captain's Patch": "THREADS_ACCESS_TOKEN_CAPTAINS_PATCH",
}
PLATFORM = "Threads"
OUTPUT_FILE = "followers.csv"
HEADER = ["date", "account", "platform", "followers"]
METRICS_FILE = "metrics.csv"
METRICS_HEADER = ["date", "account", "platform", "metric", "value"]
BASE = "https://graph.threads.net/v1.0/me"
 
 
def get(path, params, token):
    url = BASE + path + "?" + urllib.parse.urlencode(dict(params, access_token=token))
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:300].replace(token, "***")
        raise RuntimeError("Threads error {}: {}".format(e.code, body))
    except urllib.error.URLError as e:
        raise RuntimeError("Threads unreachable: {}".format(e.reason))
 
 
def followers(token):
    data = get("/threads_insights", {"metric": "followers_count"}, token)
    for item in data.get("data", []):
        if item.get("name") == "followers_count":
            if "total_value" in item:
                return int(item["total_value"]["value"])
            if item.get("values"):
                return int(item["values"][-1]["value"])
    raise RuntimeError("No followers_count returned (profiles need 100+ followers): {}".format(
        json.dumps(data)[:300]))
 
 
def metric_total(token, name, since, until):
    """Total of one insights metric over the window (handles both response shapes)."""
    data = get("/threads_insights", {"metric": name, "since": since, "until": until}, token)
    for item in data.get("data", []):
        if item.get("name") == name:
            if "total_value" in item:
                return int(item["total_value"].get("value", 0))
            return sum(int(v.get("value", 0)) for v in item.get("values", []))
    return 0
 
 
def week_metrics(token):
    until = int(time.time())
    since = until - 7 * 86400
    views = metric_total(token, "views", since, until)
    engagements = 0
    for name in ("likes", "replies", "reposts", "quotes"):
        engagements += metric_total(token, name, since, until)
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
    today, new_rows, metric_rows, failed = date.today().isoformat(), [], [], []
    for account, var in ACCOUNTS.items():
        token = os.environ.get(var, "").strip()
        if not token:
            print("Skipping {} ({} is empty)".format(account, var))
            continue
        try:
            count = followers(token)
            username = get("", {"fields": "username"}, token).get("username", "")
        except RuntimeError as e:
            failed.append(account)
            print("::error::{}: {}".format(account, e))
            continue
        new_rows.append([today, account, PLATFORM, str(count)])
        print("{} | {} | {} (@{}) | {:,}".format(today, account, PLATFORM, username, count))
        try:
            views, engagements = week_metrics(token)
            metric_rows += [[today, account, PLATFORM, "views_7d", str(views)],
                            [today, account, PLATFORM, "engagements_7d", str(engagements)]]
            print("   last 7 days: {:,} views, {:,} engagements".format(views, engagements))
        except RuntimeError as e:
            print("::warning::{} views/engagement not saved: {}".format(account, e))
    if new_rows:
        save_rows(new_rows)
    if metric_rows:
        save_metric_rows(metric_rows)
    if failed:
        sys.exit("Failed: " + ", ".join(failed))
 
 
if __name__ == "__main__":
    main()
