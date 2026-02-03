#!/usr/bin/env python3

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from read_df import read_dfs


def parse_year_month(s):
    try:
        y, m = s.split("-", 1)
        return int(y), int(m)
    except Exception as e:
        raise argparse.ArgumentTypeError("Expected YYYY-MM (e.g. 2023-05)") from e


def main():
    ap = argparse.ArgumentParser(description="Plot sense distributions for one headword.")
    ap.add_argument("--parts", nargs="+", required=True, help="One or more sensetrends shard files (000/001/...).")
    ap.add_argument("--word", required=True, help="Headword id (e.g. rag-n, nifty-j).")
    ap.add_argument("--out", required=True, help="Output figure filename (pdf/png).")
    ap.add_argument("--from", dest="from_ym", type=parse_year_month, default=(2023, 4), help="Start YYYY-MM label.")
    ap.add_argument("--usetex", action="store_true", help="Use LaTeX for text rendering (requires LaTeX).")
    ap.add_argument("--model", default=None, help="Path to AdaGram model (optional, for nearest-neighbor labels).")
    ap.add_argument("--kind", default="stackbars", choices=("stackbars", "stackplot", "plot"), help="Plot kind.")
    ap.add_argument("--no-reorder", action="store_true", help="Do not reorder senses by slope.")
    ap.add_argument("--interp", action="store_true", help="Interpolate monthly curves (smoother but slower).")
    args = ap.parse_args()

    dfs = read_dfs(args.parts)
    hw_to_df = {df.index[0]: df for df in dfs if len(df.index) > 0}
    if args.word not in hw_to_df:
        raise SystemExit(f"Headword {args.word!r} not found in provided shards.")

    model = None
    if args.model:
        import adagram

        model = adagram.Model(args.model)

    import plotword

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    plotword.plotdf(
        hw_to_df[args.word],
        fname=str(out_path),
        usetex=args.usetex,
        fromyearmonth=args.from_ym,
        kind=args.kind,
        reorder=not args.no_reorder,
        interp=args.interp,
        model=model,
    )
    return 0


if __name__ == "__main__":
    exit(main())
