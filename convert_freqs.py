#!/usr/bin/env python3

import argparse
import csv
from pathlib import Path
import sys

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
    ap.add_argument("infile", help="Input file (old block or TSV).")
    args = ap.parse_args()

    if is_block_format(args.infile):
        df = convert_block(args.infile)
    else:
        df = convert_tsv(args.infile)

    df.to_csv(sys.stdout, sep="\t", index=False, quoting=3)


if __name__ == "__main__":
    exit(main())

