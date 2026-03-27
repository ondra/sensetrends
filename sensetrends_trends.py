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

    epoch = df["epoch"] if "epoch" in df.columns else pd.Series(range(len(df)), name="epoch", index=df.index)
    freqs = df[scols].astype(float)

    if norm == "sr":
        res = freqs.div(freqs.sum(axis=1), axis=0)
        return res.fillna(0.0).assign(epoch=epoch)

    if "norm" not in df.columns:
        raise ValueError("Normalizations 'en' and 'gn' require a 'norm' column.")

    normed = freqs.div(df["norm"].astype(float), axis=0)

    if norm == "en":
        E = len(normed)
        scales = (E / normed.sum(axis=0)).replace([np.inf, -np.inf], np.nan)
        ret = normed.mul(scales, axis=1)
    elif norm == "gn":
        S, E = len(scols), len(normed)
        denom = float(normed.to_numpy().sum())
        if denom == 0.0 or np.isnan(denom):
            # Window may contain only zeros for this headword.
            ret = normed * 0.0
        else:
            ret = normed * ((S * E) / denom)
    else:
        raise ValueError(f"Unknown normalization: {norm!r}")

    return ret.fillna(0.0).assign(epoch=epoch)


def compute_trends_for_headword(df, norm, method, xs=None):
    """
    Compute trend stats for each sense column using one method.

    Returns a list of tuples compatible with DataFrame.from_records:
      (hw, sn, i, s, p)
    """
    hw = df.index[0]
    ndf = normalize_headword_df(df, norm)
    scols = [c for c in ndf.columns if c.startswith("s")]

    xs = list(range(len(ndf)))

    out = []
    for c in scols:
        series = ndf[c]
        ssum = float(series.sum())
        if ssum == 0.0 or np.isnan(ssum):
            continue
        sn = int(c[1:])
        import slope
        if method == "mk":
            i, s, p = slope.mk_intercept(xs, series)
        elif method == "lr":
            i, s, p = slope.linreg_intercept(xs, series)
        else:
            raise ValueError(f"Unknown method: {method!r}")
        out.append((hw, sn, i, s, p))
    return out


def _read_freqs_tsv(path):
    return pd.read_csv(path, sep="\t", quoting=3) # quoting=csv.QUOTE_NONE


def _select_epoch_window(group_df, epochs=0, skip_last=0):
    """
    Select a contiguous window by row position.

    Rows are assumed to be already in chronological order (oldest to newest).
    """
    if skip_last < 0:
        raise ValueError("skip_last must be >= 0")
    if epochs < 0 or epochs == 1:
        raise ValueError("epochs must be >=2, or 0 for all epochs")

    end = len(group_df) - skip_last if skip_last else len(group_df)
    if end < 0:
        end = 0

    if epochs == 0:
        start = 0
    else:
        start = max(0, end - epochs)

    return group_df.iloc[start:end]


def compute_trends_df(df, norm, method, epochs=0, skip_last=0):
    """
    Compute trends from a DataFrame in the new format (no backwards compatibility):
      hw, epoch, s0..sN, norm
    """
    if "hw" not in df.columns or "epoch" not in df.columns:
        raise ValueError("Expected columns: hw, epoch, s0..sN, norm")

    hw_rank = {hw: i for i, hw in enumerate(pd.unique(df["hw"]))}

    recs = []
    for hw, g in df.groupby("hw", sort=False):
        g = _select_epoch_window(g, epochs=epochs, skip_last=skip_last)
        if len(g) == 0:
            continue
        g = g.set_index("hw", drop=True)
        recs.extend(compute_trends_for_headword(g, norm, method=method))

    res = pd.DataFrame.from_records(recs, columns=["hw", "sn", "i", "s", "p"])
    res["rank"] = res["hw"].map(hw_rank)
    return res


def compute_trends(paths, norm, method, epochs=0, skip_last=0):
    df = pd.concat([_read_freqs_tsv(p) for p in paths], ignore_index=True)
    return compute_trends_df(df, norm, method=method, epochs=epochs, skip_last=skip_last)


def write_tsv(df, path):
    df.to_csv(path, sep="\t", index=False, quoting=3)
