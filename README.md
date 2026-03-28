# SenseTrends

Automatic detection of trending word senses in diachronic monitor corpora.

Given a compiled diachronic corpus and a trained
[Adaptive Skip-gram](https://github.com/ondra/adagram) model, SenseTrends
computes per-sense frequency time series, estimates statistical trends, and
ranks senses by the strength of their frequency change over time.

The thesis appendix in [fi-pdflatex.tex](fi-pdflatex.tex) describes the same
overall workflow. Some appendix command lines use older CLI syntax; the
commands in this README match the current binaries in this repository.

See [EXAMPLE.md](EXAMPLE.md) for the thesis-aligned walkthrough and a concrete
single-feed smoke test using `https://www.ceskenoviny.cz/sluzby/rss/zpravy.php`.

## Companion tools

SenseTrends is the final ranking and inspection layer of a larger pipeline. The
other repositories cited in the thesis are:

| Tool | Repository | Purpose | Bundled here |
|------|------------|---------|--------------|
| **feed_fetcher** | [ondra/feed_fetcher](https://github.com/ondra/feed_fetcher) | Crawl RSS/Atom feeds and download article HTML | No |
| **corp** | [ondra/corp](https://github.com/ondra/corp) | Compile and query Manatee-compatible corpora | No |
| **adagram** | [ondra/adagram](https://github.com/ondra/adagram) | Train/query Adaptive Skip-gram models (`learn`, `sensefreqs`, `senseconc`, `nearest`, `desamb`) | Core binaries are bundled |
| **slope** | [ondra/slope](https://github.com/ondra/slope) | Rust trend-estimation library behind the Python extension | Indirectly, via `slope.so` |
| **pyslope** | [ondra/pyslope](https://github.com/ondra/pyslope) | Python bindings for Mann-Kendall / linear-regression trend estimation | Yes, via `slope.so` |
| **pyadagram** | [ondra/pyadagram](https://github.com/ondra/pyadagram) | Python bindings for AdaGram model queries | Yes, via `adagram.so` / `libpyadagram.so` |

This repository contains the Python ranking/plotting code plus prebuilt
Linux/x86_64 binaries and shared objects used by that layer.

Additional external tools commonly used before corpus compilation:

- [jusText](https://corpus.tools/) for boilerplate removal
- `uninorm` and `unitok` from [corpus.tools](https://corpus.tools/) for text normalization and tokenization
- [Onion](https://corpus.tools/) for deduplication
- A lemmatizer / PoS tagger for the target language

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Reality check

Trend ranking needs a diachronic corpus with multiple epochs plus a trained
sense model. A single fresh feed crawl is enough to validate acquisition and
preprocessing, but not enough to produce stable trend estimates by itself.

## Quick start

The examples below assume you already have:

- `corpus.conf`: compiled corpus configuration
- `model.adagram`: trained AdaGram model
- a diachronic structure attribute such as `doc.month` or `doc.date`

### 1. Extract target headwords

`lswl` returns `headword<TAB>frequency`, so strip the frequency column before
feeding the list to `sensefreqs`.

```bash
lswl -l 100000 corpus.conf lempos > headwords_with_freqs.tsv
cut -f1 headwords_with_freqs.tsv > headwords.txt
```

### 2. Compute sense frequencies

Use `doc.month` for production corpora that expose monthly buckets. If your
minimal corpus only has daily dates, replace it with `doc.date`.

```bash
./sensefreqs corpus.conf lempos doc.month model.adagram \
    --nthreads 16 < headwords.txt > sensed.tsv
```

`./sensetrends` provides the same CLI shape and is used by `Makefile.wl`.

### 3. Rank trending senses

`rank_trends.py` accepts one or more `sensefreqs` output files.

```bash
python rank_trends.py sensed.tsv --method mk --norm en --out trends.tsv
```

### 4. Filter results

```bash
python scripts/filter_trends_tsv.py \
    --input trends.tsv --output filtered.tsv \
    --max-rank 30000 --max-p 0.01 --min-slope 0.01 \
    --pattern '.*'
```

### 5. Plot a single headword

```python
import pandas as pd
from plotword import plotdf
from sensetrends_trends import normalize_headword_df

df = pd.read_csv("sensed.tsv", sep="\t", quoting=3)
hw_df = df[df.hw == "agentic-j"].set_index("hw")
ndf = normalize_headword_df(hw_df, "sr")
plotdf(ndf, fname="agentic-j.pdf")
```

## Files

| File | Description |
|------|-------------|
| `rank_trends.py` | Rank sense trends from one or more TSV frequency files |
| `sensetrends_trends.py` | Normalization and slope / p-value computation |
| `plotword.py` | Sense-frequency visualization |
| `name_senses_llm.py` | LLM-based sense naming from concordances |
| `scripts/filter_trends_tsv.py` | Filter and sort ranked trend output |
| `Makefile.wl` | Local batch workflow for headword splitting, `sensefreqs`, and ranking |

## Citation

If you use SenseTrends in your research, please cite:

> Ondřej Herman and Pavel Rychlý. 2026. [Detecting Subtle Sense Shift with Polysemy-Aware Trends](https://aclanthology.org/2026.eacl-short.2/). In *Proceedings of the 19th Conference of the European Chapter of the Association for Computational Linguistics (Volume 2: Short Papers)*, pages 60–65, Rabat, Morocco. Association for Computational Linguistics.

```bibtex
@inproceedings{herman-rychly-2026-detecting,
    title = "Detecting Subtle Sense Shift with Polysemy-Aware Trends",
    author = "Herman, Ond{\v{r}}ej and Rychl{\'y}, Pavel",
    booktitle = "Proceedings of the 19th Conference of the {E}uropean Chapter of the {A}ssociation for {C}omputational {L}inguistics (Volume 2: Short Papers)",
    month = mar,
    year = "2026",
    address = "Rabat, Morocco",
    publisher = "Association for Computational Linguistics",
    pages = "60--65",
    doi = "10.18653/v1/2026.eacl-short.2"
}
```

## License

GPL-3.0
