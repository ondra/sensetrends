# SenseTrends Pipeline Example

This document follows the end-to-end process described in the thesis appendix
(`fi-pdflatex.tex`), but the command lines below are updated to the current
CLIs in the companion repositories and in this repository.

Two views are provided:

- a thesis-aligned conceptual pipeline from feeds to ranked trending senses
- a concrete single-feed Czech smoke test using
  `https://www.ceskenoviny.cz/sluzby/rss/zpravy.php`

## Prerequisites

The thesis cites these companion repositories:

- [ondra/feed_fetcher](https://github.com/ondra/feed_fetcher) for RSS/Atom crawling
- [ondra/corp](https://github.com/ondra/corp) for corpus compilation and access
- [ondra/adagram](https://github.com/ondra/adagram) for Adaptive Skip-gram training and querying
- [ondra/slope](https://github.com/ondra/slope) and [ondra/pyslope](https://github.com/ondra/pyslope) for trend estimation
- [ondra/pyadagram](https://github.com/ondra/pyadagram) for Python AdaGram queries

On this machine, local mirrors also exist in `~/rust/`:

- `~/rust/feed_fetcher`
- `~/rust/corp`
- `~/rust/adagram`
- `~/rust/slope`
- `~/rust/pyslope`
- `~/rust/pyadagram`

This repository already bundles the main AdaGram-side binaries used after the
corpus and model exist:

- `learn`
- `sensefreqs`
- `senseconc`
- `nearest`
- `desamb`
- `sensetrends`
- `slope.so`
- `adagram.so`

External preprocessing tools are still needed for a full raw-web pipeline:

- `jusText` for boilerplate removal
- `uninorm` and `unitok` for normalization/tokenization
- `onion` for deduplication
- a lemmatizer / PoS tagger for the target language

## Conceptual pipeline

### 1. Crawl web feeds

**Tool:** [FeedFetcher](https://github.com/ondra/feed_fetcher)

Create a feed list with one RSS/Atom URL per line:

```text
https://feeds.bbci.co.uk/news/rss.xml
https://rss.nytimes.com/services/xml/rss/nyt/World.xml
```

Initialize an empty plan file, then refresh it and fetch the pages:

```bash
touch plan.tsv
update plan.tsv feeds.txt --time-limit 3600
fetch plan.tsv out/pages --time-limit 3600
```

**Input:** `feeds.txt`
**Output:** `out/pages.jsonl`

Notes:

- the current `update` CLI takes positional arguments `PLANFILE FEEDS`
- the current `fetch` CLI takes positional arguments `PLANFILE OUT_PREFIX`
- `fetch plan.tsv out/pages ...` writes `out/pages.jsonl`

### 2. Extract text

**Tool:** `dump.py` from `feed_fetcher/util/`

If you want to keep the Python dependencies isolated, install `jusText` from
`corpus.tools` rather than from PyPI:

```bash
python -m venv .venv
. .venv/bin/activate
pip install requests \
    https://corpus.tools/raw-attachment/wiki/Downloads/justext-5.0.tar.gz
```

Use a jusText stoplist or a custom stopword file for the target language:

```bash
python /path/to/feed_fetcher/util/dump.py \
    --wordlist_lang English \
    out/pages.jsonl > raw_text.txt
```

**Input:** fetched JSONLines
**Output:** `<doc>...</doc>` vertical text with document metadata and paragraph boundaries

If the installed jusText build uses different stoplist names, use
`--wordlist_file` instead of `--wordlist_lang`.

### 3. Normalize and tokenize

**Tools:** `uninorm`, `unitok`

Download and unpack the `corpus.tools` `unitok` bundle, which contains both
`uninorm.py` and `unitok.py`:

```bash
curl -fsSL https://corpus.tools/raw-attachment/wiki/Downloads/unitok-4.0.tar.gz \
    -o unitok-4.0.tar.gz
tar -xzf unitok-4.0.tar.gz
```

```bash
python unitok-4.0/uninorm.py < raw_text.txt | \
    python unitok-4.0/unitok.py unitok-4.0/configs/english.py > tokenized.vert
```

**Output:** vertical text with one token per line

### 4. Deduplicate

**Tool:** [Onion](https://corpus.tools/)

```bash
onion < tokenized.vert > deduplicated.vert
```

**Output:** deduplicated vertical text

### 5. Lemmatize and PoS-tag

Use a language-appropriate tagger so each token line has at least:

- `word`
- `lempos` (lemma + part-of-speech, e.g. `bank-n`, `run-v`)

### 6. Compile corpus

**Tool:** [corp](https://github.com/ondra/corp)

Minimal corpus configuration:

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

Compile and build derived data:

```bash
encodevert -c ./corpus.conf
mkdynattr ./corpus.conf lc
mktokencov ./corpus.conf
```

**Input:** lemmatized vertical text
**Output:** compiled corpus in `./data/`

If your production corpus exposes a monthly structure attribute such as
`doc.month`, use that in the later trend steps. The minimal configuration above
uses `doc.date` because it is simpler and internally consistent.

### 7. Prepare the headword list

`lswl` emits `headword<TAB>frequency`, so split it into two files:

```bash
lswl -l 100000 ./corpus.conf lempos > headwords_with_freqs.tsv
cut -f1 headwords_with_freqs.tsv > headwords.txt
```

**Input:** compiled corpus
**Output:** `headwords.txt` with one `lempos` per line

### 8. Train the word sense model

**Tool:** `learn` from [adagram](https://github.com/ondra/adagram)

```bash
./learn ./corpus.conf lempos model.adagram \
    --dim 64 --alpha 0.15 --window 10
```

The exact training time depends on corpus size. For small smoke tests this can
be quick; for real monitor corpora it is a long-running job.

### 9. Compute sense frequencies

**Tool:** `sensefreqs`

```bash
./sensefreqs ./corpus.conf lempos doc.date model.adagram \
    --nthreads 16 < headwords.txt > sensed.tsv
```

If the corpus defines monthly bins, replace `doc.date` with `doc.month`.

Expected TSV columns:

```text
hw    epoch    s0    s1    ...    norm
```

- `s0..sN`: raw counts for each induced sense
- `norm`: total tokens in the epoch

### 10. Rank trends

**Tool:** `rank_trends.py`

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

### 11. Filter results

```bash
python scripts/filter_trends_tsv.py \
    --input trends.tsv --output filtered.tsv \
    --max-rank 30000 --max-p 0.01 --min-slope 0.01 \
    --pattern '.*'
```

### 12. Inspect results

Nearest neighbors:

```bash
echo "bank-n" | ./nearest model.adagram --compact
```

Sense concordances:

```bash
echo "bank-n" | ./senseconc ./corpus.conf lempos word model.adagram
```

Sense naming with an LLM:

```bash
python name_senses_llm.py concordances.tsv > sense_names.tsv
```

`name_senses_llm.py` requires `OPENROUTER_API_KEY`.

## Single-feed Czech smoke test

This is a minimal reproduction target for the provided feed
`https://www.ceskenoviny.cz/sluzby/rss/zpravy.php`.

It validates that the feed is live, that the fetcher can ingest it, and that
the page dump step produces corpus-ready document blocks. It is not, by itself,
a meaningful trend-ranking experiment, because one fresh single-source crawl
does not provide enough diachronic evidence.

### 1. Create a work directory

```bash
mkdir -p smoke-cs-feed/out
cd smoke-cs-feed
printf '%s\n' 'https://www.ceskenoviny.cz/sluzby/rss/zpravy.php' > feeds.txt
touch plan.tsv
```

### 2. Update the plan and fetch pages

If `update` and `fetch` are installed globally:

```bash
update plan.tsv feeds.txt --time-limit 3600
fetch plan.tsv out/pages --time-limit 3600
```

If you are using the local mirrors in `~/rust`:

```bash
cargo run --manifest-path ~/rust/feed_fetcher/Cargo.toml --bin update -- \
    plan.tsv feeds.txt --time-limit 3600

cargo run --manifest-path ~/rust/feed_fetcher/Cargo.toml --bin fetch -- \
    plan.tsv out/pages --time-limit 3600
```

Expected artifact:

```text
out/pages.jsonl
```

### 3. Extract Czech text

Create a small virtualenv for the extraction helper and install the
`corpus.tools` `jusText` build:

```bash
python -m venv .venv
. .venv/bin/activate
pip install requests \
    https://corpus.tools/raw-attachment/wiki/Downloads/justext-5.0.tar.gz
```

```bash
python ~/rust/feed_fetcher/util/dump.py \
    --wordlist_lang Czech \
    out/pages.jsonl > raw_text.txt
```

If your local jusText install uses a different Czech stoplist name, switch to
`--wordlist_file`.

Expected artifact:

```text
raw_text.txt
```

The file should contain `<doc ...>` blocks with metadata such as `title`,
`url`, `feed`, `date`, `seen`, and `downloaded`, followed by extracted
paragraphs.

### 4. Normalize and tokenize

Download and unpack the `corpus.tools` `unitok` bundle if you do not already
have it:

```bash
curl -fsSL https://corpus.tools/raw-attachment/wiki/Downloads/unitok-4.0.tar.gz \
    -o unitok-4.0.tar.gz
tar -xzf unitok-4.0.tar.gz
```

```bash
python unitok-4.0/uninorm.py < raw_text.txt | \
    python unitok-4.0/unitok.py unitok-4.0/configs/czech.py > tokenized.vert
```

Expected artifact:

```text
tokenized.vert
```

### 5. Decide whether to continue

At this point you have validated the raw acquisition side of the pipeline.

To continue all the way to ranked trends, choose one of these:

- repeat the crawl over time so the corpus gains enough temporal depth
- plug the extracted material into an already existing diachronic Czech corpus
  and model
- treat this run only as a preprocessing smoke test and stop here

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
