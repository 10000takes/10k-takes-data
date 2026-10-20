#!/usr/bin/env python3
"""
10K Takes: Instagram followers, views and engagement for the SUBSIDIARY accounts.

Finds each subsidiary's Instagram account through its Facebook Page (the Page IDs
live in collect_facebook_subsidiaries.py, so you only keep them in one place) and
saves, for each account:
  followers.csv  date,account,platform,followers
  metrics.csv    date,account,platform,metric,value   (views_7d, engagements_7d)

Needs FACEBOOK_SYSTEM_USER_TOKEN (the follower-bot system user token). That token
must include instagram_basic and instagram_manage_insights, and each Instagram
account must be a Business or Creator account linked to its Facebook Page.
Accounts with no Page ID yet, or no linked Instagram account, are skipped.
Standard library only.
"""
import os
import sys
import time
from datetime import date

from collect_facebook_subsidiaries import PAGES, FHEADER, MHEADER, FOLLOWERS_FILE, METRICS_FILE, get, merge

PLATFORM = "Instagram"
METRICS = {"views_7d": "views", "engagements_7d": "total_interactions"}


def week_total(ig_id, page_token, metric):
    until = int(time.time())
    data = get(ig_id + "/insights", {"metric": metric, "metric_type": "total_value", "period": "day",
                                     "since": until - 7 * 86400, "until": until}, page_token)
    for item in data.get("data", []):
        if item.get("name") == metric:
            if "total_value" in item:
                return int(item["total_value"].get("value", 0))
            return sum(int(v.get("value", 0)) for v in item.get("values", []))
    raise RuntimeError("{} returned no data".format(metric))


def main():
    token = os.environ.get("FACEBOOK_SYSTEM_USER_TOKEN", "").strip()
    if not token:
        sys.exit("Set FACEBOOK_SYSTEM_USER_TOKEN first.")
    today, frows, mrows, failed = date.today().isoformat(), [], [], []
    for account, page_id in PAGES.items():
        if page_id.startswith("REPLACE_"):
            print("Skipping {} (no Page ID yet)".format(account))
            continue
        try:
            page_token = get(page_id, {"fields": "access_token"}, token)["access_token"]
            link = get(page_id, {"fields": "instagram_business_account"}, page_token)
            ig = (link.get("instagram_business_account") or {}).get("id")
            if not ig:
                print("::notice::{}: no Instagram Business/Creator account is linked to this Page yet".format(account))
                continue
            info = get(ig, {"fields": "username,followers_count"}, page_token)
            count = info["followers_count"]
        except (RuntimeError, KeyError) as e:
            failed.append(account)
            print("::error::{}: {}".format(account, e))
            continue
        frows.append([today, account, PLATFORM, str(int(count))])
        line = "{} | {} | {} (@{}) | followers={:,}".format(today, account, PLATFORM, info.get("username", ""), int(count))
        for name, metric in METRICS.items():
            try:
                v = week_total(ig, page_token, metric)
                mrows.append([today, account, PLATFORM, name, str(v)])
                line += " {}={:,}".format(name, v)
            except RuntimeError as e:
                print("::warning::{} {}: {}".format(account, name, e))
        print(line)
    if frows:
        merge(FOLLOWERS_FILE, FHEADER, frows, 3)
    if mrows:
        merge(METRICS_FILE, MHEADER, mrows, 4)
    if failed:
        sys.exit("Failed: " + ", ".join(failed))


if __name__ == "__main__":
    main()
