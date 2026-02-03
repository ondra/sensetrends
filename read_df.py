from pathlib import Path

import csv
import pandas as pd


def _is_block_format(path):
    try:
        with Path(path).open("r", encoding="utf-8", errors="replace") as f:
            first = f.readline()
        return first.startswith("HW ")
    except OSError:
        return False


def _read_block_format(path):
    """
    Read the "block" format used by some experimental `sensetrends` outputs:

      HW <headword>
      s##0 <tab> v0 <tab> v1 ...
      ...
      f <tab> ...
      n <tab> ...
      HW <next headword>

    Returns one DataFrame per headword, indexed by `hw`, with columns:
      epoch, f, n, s0..sK
    """
    out = []

    cur_hw = None
    senses = {}
    f_vals = None
    n_vals = None

    def flush():
        nonlocal cur_hw, senses, f_vals, n_vals
        if cur_hw is None:
            return

        lengths = [len(v) for v in senses.values()]
        if f_vals is not None:
            lengths.append(len(f_vals))
        if n_vals is not None:
            lengths.append(len(n_vals))
        if not lengths:
            return
        L = max(lengths)

        rec = {
            "hw": [cur_hw] * L,
            "epoch": list(range(L)),
        }
        if f_vals is not None:
            rec["f"] = f_vals + [float("nan")] * (L - len(f_vals))
        if n_vals is not None:
            rec["n"] = n_vals + [float("nan")] * (L - len(n_vals))
        for sn, vals in sorted(senses.items()):
            rec[f"s{sn}"] = vals + [0.0] * (L - len(vals))

        df = pd.DataFrame(rec).set_index("hw")
        out.append(df)

        cur_hw = None
        senses = {}
        f_vals = None
        n_vals = None

    with Path(path).open("r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if not line:
                continue
            if line.startswith("HW "):
                flush()
                cur_hw = line.split(" ", 1)[1].strip()
                continue

            if cur_hw is None:
                continue

            parts = line.split("\t")
            tag = parts[0]
            if tag.startswith("s##"):
                try:
                    sn = int(tag[3:])
                except ValueError:
                    continue
                senses[sn] = [float(x) for x in parts[1:] if x != ""]
            elif tag == "f":
                f_vals = [float(x) for x in parts[1:] if x != ""]
            elif tag == "n":
                n_vals = [float(x) for x in parts[1:] if x != ""]

    flush()
    return out


def _read_table(path):
    path = Path(path)
    # Prefer TSV (what `sensetrends` typically emits), fall back to whitespace.
    df = pd.read_csv(path, sep="\t", engine="python", quoting=csv.QUOTE_NONE)
    if df.shape[1] <= 1:
        df = pd.read_csv(path, sep=r"\s+", engine="python", quoting=csv.QUOTE_NONE)
    return df


def read_df(path):
    """
    Read one `sensetrends` shard (usually 000/001/...) and return one DataFrame
    per headword.

    Expected columns include at least:
      - hw (headword identifier, e.g. "rag-n")
      - epoch (int, 0..T-1)
      - sense columns: s0, s1, ...
    Additional columns (e.g. f, n, ...) are preserved.
    """
    if _is_block_format(path):
        return _read_block_format(path)
    df = _read_table(path)

    if "hw" not in df.columns:
        raise ValueError(f"{path}: missing required column 'hw'")

#    if "epoch" in df.columns:
#        df = df.sort_values(["hw", "epoch"], kind="stable")

    out = []
    for _, g in df.groupby("hw", sort=False):
        g = g.copy()
        g = g.set_index("hw", drop=True)
        out.append(g)
    return out


def read_dfs(paths):
    out = []
    for p in paths:
        out.extend(read_df(p))
    return out
