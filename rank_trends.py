#!/usr/bin/env python3

import argparse

from sensetrends_trends import compute_trends, write_tsv


def main():
    ap = argparse.ArgumentParser(description="Rank sense trends.")
    ap.add_argument("parts", nargs="+", help="One or more input files.")
    ap.add_argument(
        "--method",
        required=True,
        choices=("mk", "lr"),
        help="Trend method: mk (Mann-Kendall/Theil-Sen) or lr (linear regression).",
    )
    ap.add_argument(
        "--norm",
        required=True,
        choices=("en", "gn", "sr"),
        help="Normalization: en, gn, sr.",
    )
    ap.add_argument(
        "--epochs",
        type=int,
        default=0,
        help="Use the last N contiguous epochs per headword (after --skip-last), 0 for all.",
    )
    ap.add_argument(
        "--skip-last",
        type=int,
        default=0,
        help="Skip K newest epochs per headword before taking --epochs window.",
    )
    ap.add_argument("--out", required=True, help="Output TSV filename.")
    ap.add_argument(
        "--sort",
        default="desc",
        choices=("asc", "desc"),
        help="Sort direction by slope column 's'.",
    )
    ap.add_argument("--lowercase", action="store_true", help="Keep only lowercase headwords.")
    ap.add_argument("--max-rank", type=int, default=None, help="Keep only rank < MAX_RANK.")
    ap.add_argument("--max-p", type=float, default=None, help="Keep only rows with p-value <= MAX_P.")
    args = ap.parse_args()

    df = compute_trends(
        args.parts,
        args.norm,
        method=args.method,
        epochs=args.epochs,
        skip_last=args.skip_last,
    )

    if args.lowercase:
        df = df[df.hw == df.hw.str.lower()]
    if args.max_rank is not None:
        df = df[df["rank"] < args.max_rank]
    if args.max_p is not None:
        df = df[df["p"] <= args.max_p]

    df = df.sort_values("s", ascending=(args.sort == "asc"), kind="stable")
    write_tsv(df, args.out)
    return 0


if __name__ == "__main__":
    exit(main())
