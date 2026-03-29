# SenseTrends Pipeline Example

This document mirrors the structure of the first appendix of the thesis
[*Automatic Detection of Word Sense Shift*](https://is.muni.cz/auth/th/tlymm/),
but uses the current command-line syntax verified in this repository.

The workflow starts with a list of web feed URLs and ends with a ranked list of
trending senses. The early steps show a minimal live crawl. The later steps use
the same commands on a compiled diachronic corpus and AdaGram model. Concrete
local stand-ins used on this machine are noted in `Agents.md`.

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

The examples below use command names such as `update`, `fetch`, `encodevert`,
`mkdynattr`, `mktokencov`, `lswl`, `learn`, `sensefreqs`, `nearest`, and
`senseconc`.

If those commands are not installed globally, use the bundled binaries:

```bash
export PATH="$PWD/bin/feed_fetcher:$PWD/bin/corp:$PWD/bin/adagram:$PWD/bin/onion:$PATH"
```

### 3. External preprocessing tools

For the raw-web stages you still need:

- `dump.py` from [ondra/feed_fetcher](https://github.com/ondra/feed_fetcher)
- `jusText`
- `uninorm`
- `unitok`
- optionally, a lemmatizer / PoS tagger for the target language

Set this to your local `feed_fetcher` checkout:

```bash
export FEED_FETCHER_REPO=/path/to/feed_fetcher
```

### 4. Working variables

Set the paths you will use during the walkthrough:

```bash
export WORKDIR="$PWD/example-workflow"
export FEEDS_FILE="$WORKDIR/feeds.txt"
export PLANFILE="$WORKDIR/plan.tsv"
export OUT_PREFIX="$WORKDIR/out/pages"
export RAW_TEXT="$WORKDIR/raw_text.txt"
export TOKENIZED_VERT="$WORKDIR/tokenized.vert"
export DEDUP_VERT="$WORKDIR/deduplicated.vert"
export CORPUS_INPUT_VERT="$WORKDIR/corpus_input.vert"
export CORPUS="$WORKDIR/corpus.conf"
export MODEL="$WORKDIR/model.adagram"
```

If you continue from an existing local corpus and model instead of building
your own from the small live crawl, set `CORPUS` and `MODEL` to those existing
paths. Concrete local examples are listed in `Agents.md`.

## Data

Create a minimal feed list:

```bash
mkdir -p "$WORKDIR/out"
cat > "$FEEDS_FILE" <<'EOF'
https://example.invalid/feed.xml
EOF
touch "$PLANFILE"
```

Replace the placeholder URL with one or more real RSS/Atom feed URLs.

## Crawl Web Feeds

Update the processing plan and fetch pages:

```bash
update "$PLANFILE" "$FEEDS_FILE" --time-limit 3600
fetch "$PLANFILE" "$OUT_PREFIX" --time-limit 3600
```

Current positional syntax:

- `update PLANFILE FEEDS`
- `fetch PLANFILE OUT_PREFIX`

Expected artifact:

```text
$OUT_PREFIX.jsonl
```

## Extract Text

The fetched data are raw web pages in JSON Lines format. Extract the salient
text with `dump.py` and `jusText`:

```bash
python "$FEED_FETCHER_REPO/util/dump.py" \
    --wordlist_lang Czech \
    "$OUT_PREFIX.jsonl" > "$RAW_TEXT"
```

If your local jusText install uses different stoplist names, use
`--wordlist_file` instead of `--wordlist_lang`.

Expected artifact:

```text
$RAW_TEXT
```

## Normalize and Tokenize the Text

Download and unpack the `corpus.tools` `unitok` bundle if needed:

```bash
curl -fsSL https://corpus.tools/raw-attachment/wiki/Downloads/unitok-4.0.tar.gz \
    -o "$WORKDIR/unitok-4.0.tar.gz"
tar -xzf "$WORKDIR/unitok-4.0.tar.gz" -C "$WORKDIR"
```

Normalize and tokenize:

```bash
python "$WORKDIR/unitok-4.0/uninorm.py" < "$RAW_TEXT" | \
    python "$WORKDIR/unitok-4.0/unitok.py" \
        "$WORKDIR/unitok-4.0/configs/czech.py" > "$TOKENIZED_VERT"
```

Expected artifact:

```text
$TOKENIZED_VERT
```

For a self-contained workflow, you can continue from here with the `word`
attribute. This is often acceptable for languages with relatively simple
morphology. For richer morphology, it is usually better to add lemmatization
and PoS tagging before training the sense model.

## Optional: Deduplicate

```bash
onion < "$TOKENIZED_VERT" > "$DEDUP_VERT"
cp "$DEDUP_VERT" "$CORPUS_INPUT_VERT"
```

If you skip this step, use `"$TOKENIZED_VERT"` as the input for the later
corpus-compilation step instead:

```bash
cp "$TOKENIZED_VERT" "$CORPUS_INPUT_VERT"
```

## Optional: Tag and Lemmatize

The main walkthrough below stays self-contained by using `word`. If you have a
tagger / lemmatizer available, this is the place to use it.

For better results, especially for morphologically richer languages such as
Czech:

- add a `lempos` column to the vertical file
- extend the corpus config with `ATTRIBUTE lempos`
- replace `word` with `lempos` in `learn`, `lswl`, `sensefreqs`, and `senseconc`

If you do not have a tagger, keep the workflow on `word`.

## Compile Corpus

Create `corpus.conf`:

```bash
cat > "$CORPUS" <<'EOF'
PATH "./data"
VERTICAL "./corpus_input.vert"
DEFAULTATTR word
ATTRIBUTE word
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
    ATTRIBUTE month {
        DYNLIB pipe
        FROMATTR date
        DYNAMIC 'cut -b1-7'
        DYNTYPE freq
    }
    ATTRIBUTE feed
    ATTRIBUTE url
}
EOF
```

Compile the corpus with Manatee tools:

```bash
encodevert -c "$CORPUS"
mktokencov "$CORPUS"
```

or, compile the corpus using the tools provided by the `corp` crate:

```bash
encodevert -c "$CORPUS"
mkrev "$CORPUS" word
mkrev "$CORPUS" doc.date
mkrev "$CORPUS" doc.feed
mkrev "$CORPUS" doc.url
mkdynattr "$CORPUS" lc
mkdynattr "$CORPUS" doc.month
mktokencov "$CORPUS"
```

The trend estimation below uses `doc.month` as the diachronic attribute.

## Train the AdaGram Model

Train the model on the compiled corpus:

```bash
learn "$CORPUS" word "$MODEL" \
    --dim 64 --alpha 0.1 --window 10 --epochs 1 --prototypes 10 --threads 16
```

Current positional syntax:

```text
learn CORPUS POSATTR MODEL
```

If you upgraded the corpus with lemmatization, replace `word` with `lempos`.
If you are continuing from an existing local corpus and model instead of the
small live crawl above, point `CORPUS` and `MODEL` at those existing paths and
match the attribute to the existing model.

## Prepare the List of Target Headwords

`lswl` emits `headword<TAB>frequency`, so split it into two files:

```bash
lswl -l 100000 "$CORPUS" word > "$WORKDIR/headwords_with_freqs.tsv"
cut -f1 "$WORKDIR/headwords_with_freqs.tsv" > "$WORKDIR/headwords.txt"
```

For a faster first pass:

```bash
head -n 5000 "$WORKDIR/headwords.txt" > "$WORKDIR/headwords.top5000.txt"
```

## Compute Sense Frequencies

```bash
sensefreqs "$CORPUS" word doc.month "$MODEL" \
    --nthreads 16 < "$WORKDIR/headwords.top5000.txt" > "$WORKDIR/sensed.tsv"
```

Expected TSV columns:

```text
hw    epoch    s0    s1    ...    norm
```

## Rank Trends

Apply trend estimation to the sense frequency distributions:

```bash
python rank_trends.py "$WORKDIR/sensed.tsv" \
    --method mk --norm en --out "$WORKDIR/trends.tsv"
```

Supported methods:

- `mk`: Mann-Kendall with Theil-Sen slope
- `lr`: ordinary least-squares linear regression

Supported normalizations:

- `en`: epoch-normalized
- `gn`: global-normalized
- `sr`: sense-relative

The output file now contains the ranked list of trending senses.

## Optional: Filter and Inspect Results

Filter the ranking:

```bash
python scripts/filter_trends_tsv.py \
    --input "$WORKDIR/trends.tsv" \
    --output "$WORKDIR/filtered.tsv" \
    --max-rank 30000 --max-p 0.01 --min-slope 0.01 \
    --pattern '.*'
```

Inspect a candidate headword with nearest neighbors:

```bash
echo "banka" | nearest "$MODEL" --compact
```

Inspect representative concordances:

```bash
echo "banka" | senseconc "$CORPUS" word word "$MODEL" \
    > "$WORKDIR/concordances.tsv"
```

Generate sense names with an LLM:

```bash
python name_senses_llm.py "$WORKDIR/concordances.tsv" \
    > "$WORKDIR/sense_names.tsv"
```

`name_senses_llm.py` requires `OPENROUTER_API_KEY` to be set for LLM access using [OpenRouter](https://openrouter.ai)

