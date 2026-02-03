import csv
import numpy as np
import pandas as pd

def sense_columns(df):
    return [c for c in df.columns if isinstance(c, str) and c.startswith("s") and c[1:].isdigit()]


def normalize_headword_df(df, norm):
    """
    Return a normalized DataFrame with the same index and an `epoch` column.

    Input format (per row):
      hw, epoch, s0..sK, norm

    Normalizations (as in the paper):
    - en (epoch-normalized):
        f_en(s,e)=|E| * (f_raw(s,e)/N(e)) / sum_e' (f_raw(s,e')/N(e'))
      (each sense sums to |E|; stable sense is ~1 everywhere)
    - gn (global-normalized):
        f_gn(s,e)=|S||E| * (f_raw(s,e)/N(e)) / sum_s',e' (f_raw(s',e')/N(e'))
      (preserves proportionality across senses within the headword)
    - sr (sense-relative):
        f_sr(s,e)=f_raw(s,e) / sum_s' f_raw(s',e)
      (sums to 1 across senses in every epoch)
    """
    scols = sense_columns(df)
    if not scols:
        raise ValueError("No sense columns (s0, s1, ...) found.")

    out = df.loc[:, scols].copy().astype(float)
    if "epoch" in df.columns:
        out["epoch"] = df["epoch"]
    else:
        out["epoch"] = np.arange(len(df), dtype=int)

    if norm in ("en", "gn"):
        if "norm" not in df.columns:
            raise ValueError("Normalization requires a 'norm' column.")
        out.loc[:, scols] = out.loc[:, scols].div(df.loc[:, "norm"], axis=0)

    if norm == "en":
        E = len(out)
        for c in scols:
            series = out[c].to_numpy(dtype=float, copy=False)
            ssum = float(np.nansum(series))
            if ssum == 0.0 or np.isnan(ssum):
                continue
            out[c] = series * (E / ssum)
    elif norm == "gn":
        S = len(scols)
        E = len(out)
        denom = float(np.nansum(out.loc[:, scols].to_numpy(dtype=float, copy=False)))
        if denom != 0.0 and not np.isnan(denom):
            out.loc[:, scols] = out.loc[:, scols] * ((S * E) / denom)
    elif norm == "sr":
        denom = out.loc[:, scols].sum(axis=1)
        out.loc[:, scols] = out.loc[:, scols].div(denom, axis=0)
    else:
        raise ValueError(f"Unknown normalization: {norm!r}")

    return out.fillna(0.0)


def compute_trends_for_headword(df, norm, xs=None):
    """
    Compute MK/Theil–Sen and LR slopes (with p-values) for each sense column.

    Returns a list of tuples compatible with DataFrame.from_records:
      (hw, s, mk_i, mk_s, mk_p, lr_i, lr_s, lr_p)
    """
    hw = df.index[0]
    ndf = normalize_headword_df(df, norm)
    scols = [c for c in ndf.columns if c.startswith("s")]

    if xs is None:
        xs = ndf["epoch"].tolist()

    out = []
    for c in scols:
        series = ndf[c]
        ssum = float(series.sum())
        if ssum == 0.0 or np.isnan(ssum):
            continue
        sn = int(c[1:])
        import slope
        mk_i, mk_s, mk_p = slope.mk_intercept(xs, series)
        lr_i, lr_s, lr_p = slope.linreg_intercept(xs, series)
        out.append((hw, sn, mk_i, mk_s, mk_p, lr_i, lr_s, lr_p))
    return out


def _read_freqs_tsv(path):
    return pd.read_csv(path, sep="\t", quoting=csv.QUOTE_NONE, engine="python")


def compute_trends_df(df, norm, min_epoch=None):
    """
    Compute trends from a DataFrame in the new format (no backwards compatibility):
      hw, epoch, s0..sN, norm
    """
    if "hw" not in df.columns or "epoch" not in df.columns:
        raise ValueError("Expected columns: hw, epoch, s0..sN, norm")

    if min_epoch is not None:
        df = df[df["epoch"] >= min_epoch]

    df = df.copy()
    hw_rank = {hw: i for i, hw in enumerate(pd.unique(df["hw"]))}

    recs = []
    for hw, g in df.groupby("hw", sort=False):
        g = g.sort_values("epoch", kind="stable")
        g = g.set_index("hw", drop=True)
        recs.extend(compute_trends_for_headword(g, norm))

    res = pd.DataFrame.from_records(
        recs, columns=["hw", "s", "mk_i", "mk_s", "mk_p", "lr_i", "lr_s", "lr_p"]
    )
    res["rank"] = res["hw"].map(hw_rank)
    return res


def compute_trends(paths, norm, min_epoch=None):
    df = pd.concat([_read_freqs_tsv(p) for p in paths], ignore_index=True)
    return compute_trends_df(df, norm, min_epoch=min_epoch)


def write_tsv(df, path):
    df.to_csv(path, sep="\t", index=False, quoting=3)
