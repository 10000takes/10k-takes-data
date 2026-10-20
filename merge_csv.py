#!/usr/bin/env python3
"""
Merge this run's NEW or CHANGED rows into the latest copy of a CSV file.

  python merge_csv.py TARGET OURS BASE KEYLEN

TARGET  the freshest file (just pulled from GitHub); updated in place
OURS    the file this run produced
BASE    the file as it was when this run started
KEYLEN  how many leading columns identify a row (3 for followers.csv, 4 for metrics.csv)

Only rows in OURS that differ from BASE are applied, so a run that started
from an old copy can never overwrite newer data. Standard library only.
"""
import csv
import sys


def read(path):
    try:
        with open(path, newline="", encoding="utf-8") as f:
            rows = [r for r in csv.reader(f) if r]
    except FileNotFoundError:
        return None, []
    if rows and rows[0] and rows[0][0] == "date":
        return rows[0], rows[1:]
    return None, rows


def main():
    target, ours, base, k = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
    t_head, t_rows = read(target)
    o_head, o_rows = read(ours)
    _, b_rows = read(base)
    header = t_head or o_head
    base_map = {tuple(r[:k]): r for r in b_rows}
    merged = {tuple(r[:k]): r for r in t_rows}
    applied = 0
    for r in o_rows:
        if base_map.get(tuple(r[:k])) != r:
            merged[tuple(r[:k])] = r
            applied += 1
    with open(target, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if header:
            w.writerow(header)
        for key in sorted(merged):
            w.writerow(merged[key])
    print("{}: applied {} new or changed row(s)".format(target, applied))


if __name__ == "__main__":
    main()
