#!/usr/bin/env python3

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from sensetrends_trends import compute_trends, write_tsv


def main():
    ap = argparse.ArgumentParser(
        description="Rank sense trends from sensetrends shard outputs (TSV output via pandas.to_csv)."
    )
    ap.add_argument("--parts", nargs="+", required=True, help="One or more shard files (000/001/...).")
    ap.add_argument(
        "--norm",
        required=True,
        choices=("en", "gn", "sr"),
        help="Normalization (paper): en, gn, sr.",
    )
    ap.add_argument("--min-epoch", type=int, default=None, help="Drop rows with epoch < MIN_EPOCH.")
    ap.add_argument("--out", required=True, help="Output TSV filename.")
    ap.add_argument(
        "--sort-by",
        default="lr_s",
        choices=("mk_s", "lr_s", "mk_p", "lr_p"),
        help="Sort key.",
    )
    ap.add_argument("--ascending", action="store_true", help="Sort ascending (default: descending for slopes).")
    ap.add_argument("--lower-only", action="store_true", help="Keep only headwords equal to their lowercase form.")
    ap.add_argument("--max-rank", type=int, default=None, help="Keep only rank < MAX_RANK.")
    ap.add_argument("--max-p", type=float, default=None, help="Keep only rows with chosen p-value <= MAX_P.")
    ap.add_argument("--positive-only", action="store_true", help="Keep only positive slopes (based on --sort-by).")
    args = ap.parse_args()

    df = compute_trends(args.parts, args.norm, min_epoch=args.min_epoch)

    if args.lower_only:
        df = df[df.hw == df.hw.str.lower()]
    if args.max_rank is not None:
        df = df[df["rank"] < args.max_rank]
    if args.max_p is not None:
        if args.sort_by not in ("mk_p", "lr_p"):
            pcol = "lr_p"
        else:
            pcol = args.sort_by
        df = df[df[pcol] <= args.max_p]
    if args.positive_only:
        if args.sort_by in ("mk_s", "lr_s"):
            df = df[df[args.sort_by] > 0]

    default_ascending = args.ascending
    if not args.ascending and args.sort_by in ("mk_p", "lr_p"):
        default_ascending = True

    df = df.sort_values(args.sort_by, ascending=default_ascending, kind="stable")
    write_tsv(df, args.out)
    return 0


if __name__ == "__main__":
    exit(main())
