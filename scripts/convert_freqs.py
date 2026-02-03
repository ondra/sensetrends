#!/usr/bin/env python3

import argparse
import csv
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import pandas as pd

from read_df import read_df


def is_block_format(path):
    with Path(path).open("r", encoding="utf-8", errors="replace") as f:
        return f.readline().startswith("HW ")


def convert_block(path):
    dfs = read_df(path)
    if not dfs:
        return pd.DataFrame()

    max_s = -1
    for df in dfs:
        for c in df.columns:
            if isinstance(c, str) and c.startswith("s") and c[1:].isdigit():
                max_s = max(max_s, int(c[1:]))
    scols = [f"s{i}" for i in range(max_s + 1)]

    out = []
    for df in dfs:
        hw = df.index[0]
        tmp = df.reset_index()
        if "epoch" not in tmp.columns:
            tmp["epoch"] = range(len(tmp))
        if "n" in tmp.columns and "norm" not in tmp.columns:
            tmp = tmp.rename(columns={"n": "norm"})

        keep = ["hw", "epoch", "norm"] + [c for c in scols if c in tmp.columns]
        tmp = tmp.loc[:, keep]
        for c in scols:
            if c not in tmp.columns:
                tmp[c] = 0.0
        tmp["hw"] = hw
        tmp = tmp.loc[:, ["hw", "epoch"] + scols + ["norm"]]
        out.append(tmp)

    return pd.concat(out, ignore_index=True).sort_values(["hw", "epoch"], kind="stable")


def convert_tsv(path):
    df = pd.read_csv(path, sep="\t", quoting=csv.QUOTE_NONE, engine="python")

    if "hw" not in df.columns or "epoch" not in df.columns:
        raise SystemExit("Expected TSV with columns: hw, epoch, s0..sN, norm")

    if "norm" not in df.columns:
        if "n" in df.columns:
            df = df.rename(columns={"n": "norm"})
        else:
            raise SystemExit("Expected a 'norm' column (or legacy 'n').")

    scols = sorted([c for c in df.columns if isinstance(c, str) and c.startswith("s") and c[1:].isdigit()], key=lambda x: int(x[1:]))
    if not scols:
        raise SystemExit("No sense columns found (s0..sN).")

    keep = ["hw", "epoch"] + scols + ["norm"]
    return df.loc[:, keep].sort_values(["hw", "epoch"], kind="stable")


def main():
    ap = argparse.ArgumentParser(description="Convert old sensetrends frequency formats into the new TSV format.")
    ap.add_argument("--in", dest="inp", required=True, help="Input file (old block or TSV).")
    ap.add_argument("--out", required=True, help="Output TSV (hw, epoch, s0..sN, norm).")
    args = ap.parse_args()

    if is_block_format(args.inp):
        df = convert_block(args.inp)
    else:
        df = convert_tsv(args.inp)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, sep="\t", index=False, quoting=3)
    return 0


if __name__ == "__main__":
    exit(main())

