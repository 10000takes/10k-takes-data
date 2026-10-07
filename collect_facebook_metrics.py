#!/usr/bin/env python3
"""
10K Takes: Facebook Page views and engagement collector (main Page).

Saves two rows to metrics.csv (date,account,platform,metric,value):
  views_7d         Page media views over the last 7 days (Meta's replacement
                   for the retired "impressions" metric)
  engagements_7d   post engagements over the last 7 days

Needs FACEBOOK_PAGE_ID and FACEBOOK_PAGE_TOKEN (same secrets as the follower
script). The token must carry the read_insights permission.
Standard library only.
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

GRAPH_VERSION = "v26.0"
ACCOUNT = "10K Takes"
PLATFORM = "Facebook"
OUT = "metrics.csv"
HEADER = ["date", "account", "platform", "metric", "value"]
METRICS = {"views_7d": "page_media_view", "engagements_7d": "page_post_engagements"}


def week_total(page_id, token, metric):
    until = int(time.time())
    since = until - 7 * 86400
    url = "https://graph.facebook.com/{}/{}/insights?".format(GRAPH_VERSION, page_id) + \
        urllib.parse.urlencode({"metric": metric, "period": "day", "since": since, "until": until})
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError("{} error {}: {}".format(metric, e.code, e.read().decode("utf-8", "replace")[:300]))
    except urllib.error.URLError as e:
        raise RuntimeError("{} unreachable: {}".format(metric, e.reason))
    for item in data.get("data", []):
        if item.get("name") == metric:
            return sum(int(v.get("value") or 0) for v in item.get("values", []) if isinstance(v.get("value"), (int, float)))
    raise RuntimeError("{} returned no data: {}".format(metric, json.dumps(data)[:200]))


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
    page_id = os.environ.get("FACEBOOK_PAGE_ID", "").strip()
    token = os.environ.get("FACEBOOK_PAGE_TOKEN", "").strip()
    if not page_id or not token:
        sys.exit("Set FACEBOOK_PAGE_ID and FACEBOOK_PAGE_TOKEN first.")
    today, rows, failed = date.today().isoformat(), [], []
    for name, metric in METRICS.items():
        try:
            value = week_total(page_id, token, metric)
        except RuntimeError as e:
            failed.append(name)
            print("::warning::{}".format(e))
            continue
        rows.append([today, ACCOUNT, PLATFORM, name, str(value)])
        print("{} | {} | {} | {}={:,}".format(today, ACCOUNT, PLATFORM, name, value))
    if rows:
        save(rows)
    if failed:
        sys.exit("Not saved: " + ", ".join(failed))


if __name__ == "__main__":
    main()
