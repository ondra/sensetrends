#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = ("hw", "s", "p", "rank")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Filter trend-output TSV rows by rank/p/slope/regex/lowercase-start."
    )
    ap.add_argument("--input", required=True, help="Input TSV path.")
    ap.add_argument("--output", required=True, help="Output TSV path.")
    ap.add_argument("--max-rank", required=True, type=int, help="Keep rows with rank < MAX_RANK.")
    ap.add_argument("--max-p", required=True, type=float, help="Keep rows with p <= MAX_P.")
    ap.add_argument(
        "--min-slope",
        required=True,
        type=float,
        help="Slope threshold value used by --slope-mode.",
    )
    ap.add_argument(
        "--slope-mode",
        choices=("ge", "abs", "le"),
        default="ge",
        help="Slope filter mode: ge=>s>=min, abs=>|s|>=min, le=>s<=-min.",
    )
    ap.add_argument("--pattern", required=True, help="Regex pattern applied to full 'hw' field.")
    ap.add_argument(
        "--sort",
        choices=("asc", "desc"),
        default="desc",
        help="Sort by slope column 's' (stable sort).",
    )
    return ap.parse_args()


def _ensure_columns(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise SystemExit(f"Missing required columns: {', '.join(missing)}")


def _compile_regex(pattern: str) -> re.Pattern[str]:
    try:
        return re.compile(pattern)
    except re.error as exc:
        raise SystemExit(f"Invalid regex pattern {pattern!r}: {exc}") from exc


def _startswith_lower(s: object) -> bool:
    if not isinstance(s, str) or not s:
        return False
    return s[0].islower()


def _apply_slope_filter(df: pd.DataFrame, mode: str, min_slope: float) -> pd.DataFrame:
    if mode == "ge":
        return df[df["s"] >= min_slope]
    if mode == "abs":
        return df[df["s"].abs() >= min_slope]
    if mode == "le":
        return df[df["s"] <= -min_slope]
    raise SystemExit(f"Unsupported slope mode: {mode}")


def run(args: argparse.Namespace) -> int:
    in_path = Path(args.input)
    out_path = Path(args.output)

    df = pd.read_csv(in_path, sep="\t", quoting=csv.QUOTE_NONE)
    _ensure_columns(df)
    regex = _compile_regex(args.pattern)

    total_in = len(df)

    for col in ("rank", "p", "s"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["rank", "p", "s"]).copy()
    after_numeric = len(df)

    mask_lower = df["hw"].map(_startswith_lower)
    mask_regex = df["hw"].astype(str).map(lambda x: bool(regex.search(x)))

    df = df[mask_lower & mask_regex]
    after_text = len(df)

    df = df[df["rank"] < args.max_rank]
    after_rank = len(df)

    df = df[df["p"] <= args.max_p]
    after_p = len(df)

    df = _apply_slope_filter(df, args.slope_mode, args.min_slope)
    after_slope = len(df)

    df = df.sort_values("s", ascending=(args.sort == "asc"), kind="stable")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, sep="\t", index=False, quoting=csv.QUOTE_NONE)

    print(f"input_rows\t{total_in}")
    print(f"after_numeric\t{after_numeric}")
    print(f"after_lowercase_and_regex\t{after_text}")
    print(f"after_rank\t{after_rank}")
    print(f"after_p\t{after_p}")
    print(f"after_slope\t{after_slope}")
    print(f"written\t{out_path}")

    return 0


def main() -> int:
    return run(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
