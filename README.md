# SenseTrends

This repository contains code for identifying trending senses within text corpora.

## Python setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

Other Dependencies:
- [`corp`](https://github.com/ondra/corp) for Manatee-compatible corpus processing
- [`pyslope`](https://github.com/ondra/pyslope) for statistical trend
- [`adagram`](https://github.com/ondra/adagram) for Adaptive Skip-Gram WSI model operations

Prebuilt binaries for Linux/x86\_64 are provided in this directory.

## Overview
The input is a compiled diachronic corpus and a corresponding Adaptive Skip-gram model.

To estimate the trends of the senses, the following steps take place:
 1. List of candidate headwords is extracted.
 2. The list is split into batches of 1000 headwords.
 3. Diachronic sense frequencies for each of the headwords are calculated.
 4. The frequencies are normalized, and the trend is estimated.
 5. The wordlist is ordered by the trend.

The output is a list of candidate words/senses, whose usages gained frequency over time.

## Data / model expectations

This repo does **not** ship large artifacts (trained models, corpus registries, or `sensetrends` output shards).

The plotting code expects:
- one or more `sensetrends` output files (typically produced by `Makefile.wl` into `sensed/<MODEL>/000`, `001`, …)
- optionally an AdaGram model file to label senses by nearest neighbors

## Plot a single headword

```bash
python scripts/plot_word.py \
  --parts sensed/trends_en_first_20250404.lempos.e1.d64.w10.a1/001 \
  --word nifty-j \
  --from 2023-05 \
  --model models/trends_en_first_20250404.lempos.e1.d64.w10.a1 \
  --out nifty-j.pdf
```

If you omit `--model`, plots will use numeric sense IDs without nearest-neighbor labels.

## Rank trending senses (TSV)

```bash
python scripts/rank_trends.py \
  --parts freqs.tsv \
  --norm sr \
  --min-epoch 20 \
  --lower-only --max-rank 30000 --max-p 1e-8 --positive-only \
  --sort-by lr_s \
  --out trends.tsv
```

Expected input format is TSV (no quoting) with columns:
`hw`, `epoch`, `s0..sN`, `norm` (total token count within epoch).

### Convert old formats

```bash
python scripts/convert_freqs.py --in 015 --out freqs.tsv
```

## Build the paper

```bash
latexmk -pdf eacl2026_sensetrends.tex
```

## Makefiles (local paths)

`Makefile.models` and `Makefile.wl` are kept for reference but include site-specific paths. To avoid editing tracked files, copy `config.mk.example` to `config.mk` and adjust the paths.

```bash
cp config.mk.example config.mk
```
