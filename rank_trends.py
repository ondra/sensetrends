#!/usr/bin/env python3

import argparse
import sys

from sensetrends_trends import compute_trends, write_tsv


def main():
    ap = argparse.ArgumentParser(description="Rank sense trends.")
    ap.add_argument("parts", nargs="+", help="One or more input files.")
    ap.add_argument(
        "--norm",
        required=True,
        choices=("en", "gn", "sr"),
        help="Normalization: en, gn, sr.",
    )
    ap.add_argument("--min-epoch", type=int, default=None, help="Drop rows with epoch < MIN_EPOCH.")
    ap.add_argument("--out", required=True, help="Output TSV filename.")
    ap.add_argument(
        "--sort-by",
        default="mk_s",
        choices=("mk_s", "lr_s"),
        help="Sort key.",
    )
    ap.add_argument("--lowercase", action="store_true", help="Keep only lowercase headwords.")
    ap.add_argument("--max-rank", type=int, default=None, help="Keep only rank < MAX_RANK.")
    ap.add_argument("--max-p", type=float, default=None, help="Keep only rows with chosen p-value <= MAX_P.")
    args = ap.parse_args()

    df = compute_trends(args.parts, args.norm, min_epoch=args.min_epoch)

    if args.lowercase:
        df = df[df.hw == df.hw.str.lower()]
    if args.max_rank is not None:
        df = df[df["rank"] < args.max_rank]
    if args.max_p is not None:
        if args.sort_by == "mk_s":
            pcol = "mk_p"
        else:
            pcol = "mk_s"
        df = df[df[pcol] <= args.max_p]

    df = df.sort_values(args.sort_by, ascending=False, kind="stable")
    write_tsv(df, args.out)
    return 0


if __name__ == "__main__":
    exit(main())
