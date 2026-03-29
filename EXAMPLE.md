# SenseTrends Pipeline Example

This document describes an example of the complete workflow for trending sense detection from web corpora, the same as the first appendix of my thesis ([Automatic Detection of Word Sense Shift](https://is.muni.cz/auth/th/tlymm/)) with some small fixes.

The example has two connected parts:

- a live Czech feed crawl and preprocessing run using
  `https://www.ceskenoviny.cz/sluzby/rss/zpravy.php`
- a continuation on an existing Czech diachronic corpus and AdaGram model to
  compute sense frequencies, rank trends, and inspect the results

## Prerequisites

### 1. Python environment

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the Python scripts from the repository root so they can import the bundled
`slope.so` and `adagram.so` modules.

### 2. Command availability

The examples below use installed command names such as `update`, `fetch`,
`encodevert`, `lswl`, `learn`, `sensefreqs`, `nearest`, and `senseconc`.

If those commands are not installed globally, you can use the binaries bundled
in this checkout by exporting `PATH` once:

```bash
export PATH="$PWD/bin/feed_fetcher:$PWD/bin/corp:$PWD/bin/adagram:$PWD/bin/onion:$PATH"
```

### 3. External preprocessing tools

For the raw-web stages you still need:

- `dump.py` from [ondra/feed_fetcher](https://github.com/ondra/feed_fetcher)
- `jusText`
- `uninorm`
- `unitok`
- a Czech lemmatizer / PoS tagger if you want to compile your own corpus from
  the freshly fetched material

Set this to your local `feed_fetcher` checkout:

```bash
export FEED_FETCHER_REPO=/path/to/feed_fetcher
```

## Part 1: Crawl and Preprocess a Live Czech Feed

### 1. Create a work directory

```bash
mkdir -p smoke-cs-feed/out
cd smoke-cs-feed
printf '%s\n' 'https://www.ceskenoviny.cz/sluzby/rss/zpravy.php' > feeds.txt
touch plan.tsv
```

### 2. Update the plan and fetch pages

```bash
update plan.tsv feeds.txt --time-limit 3600
fetch plan.tsv out/pages --time-limit 3600
```

Expected artifact:

```text
out/pages.jsonl
```

The current CLIs are positional:

- `update PLANFILE FEEDS`
- `fetch PLANFILE OUT_PREFIX`

### 3. Extract Czech text

If you want to keep the extractor dependencies separate, create a helper
environment and install the `corpus.tools` `jusText` build:

```bash
python -m venv .venv-dump
source .venv-dump/bin/activate
pip install requests \
    https://corpus.tools/raw-attachment/wiki/Downloads/justext-5.0.tar.gz
```

Run the extractor from your local `feed_fetcher` checkout:

```bash
python "$FEED_FETCHER_REPO/util/dump.py" \
    --wordlist_lang Czech \
    out/pages.jsonl > raw_text.txt
```

If your local jusText install uses different stoplist names, use
`--wordlist_file` instead of `--wordlist_lang`.

Expected artifact:

```text
raw_text.txt
```

The file should contain `<doc ...>` blocks with metadata such as `title`,
`url`, `feed`, `date`, `seen`, and `downloaded`, followed by extracted
paragraphs.

### 4. Normalize and tokenize

Download and unpack the `corpus.tools` `unitok` bundle if needed:

```bash
curl -fsSL https://corpus.tools/raw-attachment/wiki/Downloads/unitok-4.0.tar.gz \
    -o unitok-4.0.tar.gz
tar -xzf unitok-4.0.tar.gz
```

```bash
python unitok-4.0/uninorm.py < raw_text.txt | \
    python unitok-4.0/unitok.py unitok-4.0/configs/czech.py > tokenized.vert
```

Expected output produced:

```text
tokenized.vert
```

### 5. Deduplicate

```bash
onion < tokenized.vert > deduplicated.vert
```

### 6. Lemmatize and PoS-tag

Use a Czech tagger so each token line contains at least:

- `word`
- `lempos`

At that point you are ready either to compile your own diachronic corpus over
time or to continue with an existing Czech corpus and model.

## Part 2: Continue on a Real Czech Diachronic Corpus

The following commands use an already compiled Czech corpus and an already
trained AdaGram model that are present on this machine:

```bash
export CORPUS=/mnt/data/ondra/registry/trends_cs_first_20260208
export MODEL=models/trends_cs_first_20260208.lempos.e1.d64.w10.a1.p10
```

This corpus already exposes monthly bins, so the diachronic attribute used
below is `doc.month`.

### 7. Prepare the headword list

`lswl` emits `headword<TAB>frequency`, so split it into two files:

```bash
lswl -l 100000 "$CORPUS" lempos > headwords_with_freqs.tsv
cut -f1 headwords_with_freqs.tsv > headwords.txt
```

For a faster first pass, you can limit the list:

```bash
head -n 5000 headwords.txt > headwords.top5000.txt
```

### 8. Train a model if you need your own

If you are building your own corpus rather than reusing the existing model, the
current `learn` CLI is:

```bash
learn corpus.conf lempos model.adagram \
    --dim 64 --alpha 0.1 --window 10 --epochs 1 --prototypes 10
```

For the rest of this example we reuse the existing Czech model in `$MODEL`.

### 9. Compute sense frequencies

```bash
sensefreqs "$CORPUS" lempos doc.month "$MODEL" \
    --nthreads 16 < headwords.top5000.txt > sensed.tsv
```

Current argument order:

```text
sensefreqs CORPUS POSATTR DIAATTR MODEL
```

Expected TSV columns:

```text
hw    epoch    s0    s1    ...    norm
```

### 10. Rank trends

```bash
python rank_trends.py sensed.tsv --method mk --norm en --out trends.tsv
```

Supported methods:

- `mk`: Mann-Kendall with Theil-Sen slope
- `lr`: ordinary least-squares linear regression

Supported normalizations:

- `en`: epoch-normalized
- `gn`: global-normalized
- `sr`: sense-relative

### 11. Filter the ranking

```bash
python scripts/filter_trends_tsv.py \
    --input trends.tsv --output filtered.tsv \
    --max-rank 30000 --max-p 0.01 --min-slope 0.01 \
    --pattern '.*'
```

### 12. Inspect a candidate headword

Nearest neighbors:

```bash
echo "banka-n" | nearest "$MODEL" --compact
```

Sense concordances:

```bash
echo "banka-n" | senseconc "$CORPUS" lempos word "$MODEL"
```

Sense naming with an LLM:

```bash
python name_senses_llm.py concordances.tsv > sense_names.tsv
```

`name_senses_llm.py` requires `OPENROUTER_API_KEY`.

## Optional: Compile Your Own Corpus

If you want to continue from the freshly fetched Czech material instead of
switching to the existing corpus above, the minimal corpus-compilation shape is:

```ini
PATH "./data"
VERTICAL "./lemmatized.vert"
DEFAULTATTR word
ATTRIBUTE word
ATTRIBUTE lempos
ATTRIBUTE lc {
    DYNLIB internal
    DYNTYPE freq
    DYNAMIC utf8lowercase
    FROMATTR word
}
STRUCTURE p
STRUCTURE g
STRUCTURE doc {
    ATTRIBUTE date
    ATTRIBUTE feed
    ATTRIBUTE url
}
```

Then compile it with:

```bash
encodevert -c ./corpus.conf
mkdynattr ./corpus.conf lc
mktokencov ./corpus.conf
```

If your corpus later exposes monthly bins such as `doc.month`, use that in the
trend steps. Otherwise start with `doc.date`.

## Python API

```python
import slope
import adagram

# Trend estimation
slope.mk([0, 1, 2, 3], [10, 12, 15, 18])         # (slope, p_value)
slope.linreg([0, 1, 2, 3], [10, 12, 15, 18])     # (slope, p_value)

# Model queries
model = adagram.Model("model.adagram")
model.nearest_all("bank-n", num_neighbors=5, min_freq=100)
model.desamb("bank-n", ["central-j", "rate-n"])
```
