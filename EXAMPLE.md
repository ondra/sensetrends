# SenseTrends: Complete Pipeline Example

This document describes the full workflow from raw web feeds to ranked trending senses. Each step lists the tool used, its inputs, outputs, and an example command.

## Overview

```
Feeds → HTML → text → tokens → deduplicated → lemmatized → corpus → model → sense freqs → trends
```

## Step 1: Crawl web feeds

**Tool:** [FeedFetcher](https://github.com/ondra/feed_fetcher)

Periodically download articles from RSS/Atom feeds. In production, run 4 times per day.

```bash
update plan.tsv --feeds feeds.txt --timeout 3600
fetch plan.tsv --output outdir/ --timeout 3600
```

**Input:** `feeds.txt` — one feed URL per line.
**Output:** JSONLine files, one page per line (HTML + metadata).

## Step 2: Extract text

**Tool:** jusText (from [corpus.tools](https://corpus.tools/))

Remove boilerplate (navigation, ads) and extract salient paragraphs.

```bash
dump.py --stoplist english < pages.jsonl > raw_text.txt
```

## Step 3: Normalize and tokenize

**Tools:** uninorm, unitok

```bash
uninorm < raw_text.txt | unitok --language english > tokenized.vert
```

**Output:** Vertical format (one token per line with `<doc>` structure boundaries).

## Step 4: Deduplicate

**Tool:** [Onion](https://corpus.tools/)

Remove paragraphs with 70%+ overlapping shingles.

```bash
onion < tokenized.vert > deduplicated.vert
```

## Step 5: Lemmatize and POS-tag

Use a lemmatizer appropriate for your language. The output should add a `lempos` column (lemma + part-of-speech tag, e.g. `bank-n`, `run-v`).

## Step 6: Compile corpus

**Tool:** [corp](https://github.com/ondra/corp)

Create a corpus configuration file (`corpus.conf`):

```
PATH "/path/to/corpus/data"
ATTRIBUTE word
ATTRIBUTE lempos
ATTRIBUTE lc {
  DYNLIB internal
  DYNTYPE freq
  DYNFUN utf8lowercase
  FROMATTR word
}
STRUCTURE doc {
  ATTRIBUTE month
  ATTRIBUTE feed
  ATTRIBUTE url
}
```

Compile:

```bash
encodevert -c corpus.conf < lemmatized.vert
mkdynattr corpus.conf lc
mkdynattr corpus.conf doc.month
mktokencov corpus.conf
```

## Step 7: Prepare headword list

Extract the most frequent headwords from the corpus:

```bash
lswl -l100000 corpus.conf lempos > headwords.txt
```

This produces one headword per line (e.g. `bank-n`, `run-v`).

## Step 8: Train word sense model

**Tool:** `learn` (from [adagram](https://github.com/ondra/adagram))

```bash
learn corpus.conf lempos model.adagram \
    --dim 64 --alpha 0.15 --window 10
```

**Hyperparameters:**
- `--dim` (64): embedding dimensionality
- `--alpha` (0.15): sense concentration — lower values produce more senses
- `--window` (10): context window size — 5 halves training time
- `--prototypes` (10): maximum senses per word

Training takes ~30 hours for a 10 billion token corpus on 12 threads.

## Step 9: Compute sense frequencies

**Tool:** `sensefreqs`

```bash
sensefreqs corpus.conf model.adagram lempos doc.month \
    --nthreads 16 < headwords.txt > sensed.tsv
```

**Output format** (TSV, one row per headword per epoch):

```
hw        epoch    s0    s1    s2    ...  norm
bank-n    2025-01  4033  3287  1396  ...  378310476
bank-n    2025-02  3536  3625  1135  ...  362236432
```

- `s0`–`sN`: raw sense frequency counts
- `norm`: total corpus tokens in the epoch (for normalization)

Performance: top 1,000 headwords in ~1 hour; next 99,000 in another hour.

## Step 10: Rank trends

**Tool:** `rank_trends.py`

```bash
python rank_trends.py sensed.tsv --method mk --norm en --out trends.tsv
```

**Methods:**
- `mk`: Mann-Kendall test with Theil-Sen slope (robust, non-parametric)
- `lr`: Ordinary least-squares linear regression

**Normalizations:**
- `en` (epoch-normalized): each sense sums to |E| across epochs; a stable sense scores ~1 everywhere
- `gn` (global-normalized): preserves proportionality across senses
- `sr` (sense-relative): senses sum to 1 within each epoch

**Output format** (TSV):

```
hw       sn   i      s       p        rank
bank-n   0    0.788  0.039   0.0112   858
bank-n   1    0.871  0.025   0.0112   858
bank-n   4    1.119  -0.026  0.0335   858
```

- `s`: slope (positive = increasing trend)
- `p`: p-value (statistical significance)
- `rank`: corpus frequency rank

**Filtering:**

```bash
python scripts/filter_trends_tsv.py \
    --input trends.tsv --output filtered.tsv \
    --max-rank 30000 --max-p 0.01 --min-slope 0.01 \
    --pattern '.*'
```

Options: `--max-rank` (frequency rank cutoff), `--max-p` (significance), `--min-slope` (minimum trend strength), `--slope-mode` (ge/abs/le), `--pattern` (regex on headword).

## Inspection tools

### Nearest neighbors

**Tool:** `nearest`

```bash
echo "bank-n" | nearest model.adagram --compact
```

```
bank-n  0  rate-n Boe-n decision-n RBA-n Reserve-n
bank-n  2  station-n brick-n portable-j
bank-n  4  edge-n eastern-j western-j side-n shore-n river-n
```

~21 headwords/second.

### Concordances

**Tool:** `senseconc`

```bash
echo "bank-n" | senseconc corpus.conf lempos word model.adagram
```

```
hw      sn  prob  lctx                     kw    rctx
bank-n  0   1.0   pressure on central      bank  to cut interest rates
bank-n  4   1.0   butterflies along the    banks of the Xingu River
bank-n  8   1.0   stocking community food  banks with pet food
```

### Sense naming

**Tool:** `name_senses_llm.py`

```bash
python name_senses_llm.py concordances.tsv > sense_names.tsv
```

Uses an LLM to generate short descriptions for each sense cluster based on concordance examples. Requires `OPENROUTER_API_KEY` environment variable.

## Python API

```python
import slope
import adagram

# Trend estimation
slope.mk([0, 1, 2, 3], [10, 12, 15, 18])       # (Theil-Sen slope, p-value)
slope.linreg([0, 1, 2, 3], [10, 12, 15, 18])    # (OLS slope, p-value)

# Model queries
model = adagram.Model("model.adagram")
model.nearest_all("bank-n", num_neighbors=5, min_freq=100)
model.desamb("bank-n", ["central-j", "rate-n"])

# Normalization and plotting
from sensetrends_trends import normalize_headword_df, compute_trends
from plotword import plotdf, plotx
```
