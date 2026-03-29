# SenseTrends Pipeline Example

This page provides a specific example of how a trending sense detection pipeline based on corpora crawled from RSS feeds might look like. The structure corresponds to the first appendix of my thesis [_Automatic Detection of Word Sense Shift_](https://is.muni.cz/auth/th/tlymm/), with some additional details and fixes.


The initial starting point is a list of web feed URLs and the end result is a ranked list of trending senses.

## Prerequisites

For the web crawl processing, you need:

- `jusText` from [corpus.tools](https://corpus.tools) for boilerplate removal. Use the `corpus.tools` jusText package, forks use incompatible API.
- Python `requests` library, from which some convenience header parsing routines are used.
- `unitok` and `uninorm` from [corpus.tools](https://corpus.tools).
- Optionally, a lemmatizer / PoS tagger for the target language.

The SenseTrends scripts need:

- `pandas` and `numpy` for efficient TSV I/O and data analysis functionality.
- `matplotlib` and `scipy` for plotting support.

### 1. Python environment

The Python dependencies are best installed in a `venv` to keep them separate from the rest of the system. From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install pandas numpy
# optional, for plotting support:
pip install scipy matplotlib
# for text extraction from FeedFetcher dumps
pip install requests \
    https://corpus.tools/raw-attachment/wiki/Downloads/justext-5.0.tar.gz
```

Run the Python scripts from the repository root so they can import the bundled
`slope.so` and `adagram.so` modules.

### 2. Install `unitok`

```bash
curl -fsSL https://corpus.tools/raw-attachment/wiki/Downloads/unitok-4.0.tar.gz \
    -o "$WORKDIR/unitok-4.0.tar.gz"
tar -xzf "$WORKDIR/unitok-4.0.tar.gz" -C "$WORKDIR"
```

### 3. Binary programs

The examples below use unqualified command names of the tools. You can install them from the upstream repositories, or you can use the bundled binaries by adding them on PATH:

```bash
export PATH="$PWD/bin/feed_fetcher:$PWD/bin/corp:$PWD/bin/adagram:$PWD/bin/onion:$PATH"
```

## Input Data

Create a list of feeds. Atom, RSS, JSONFeed formats are supported:

```bash
mkdir -p out
cat > feeds.txt <<'EOF'
https://example.invalid/feed.xml
EOF
touch plan.tsv
```

Replace the placeholder URL with one or more real RSS/Atom feed URLs.

## Crawl Web Feeds

Update the processing plan and fetch pages:

```bash
update plan.tsv feeds.txt --time-limit 3600
fetch plan.tsv out/pages --time-limit 3600
```

Run this periodically until you build a large enough corpus.

## Extract Text

The fetched data are raw web pages in JSON Lines format. Extract the salient
text with `dump.py` and `jusText`:

```bash
dump.py --wordlist_lang English \
    out/pages.jsonl > raw_text.txt
```

If your local jusText install uses different stoplist names, use
`--wordlist_file` instead of `--wordlist_lang`.

## Normalize and Tokenize the Text

Apply Unicode normalization and split the text into tokens:

```bash
python unitok-4.0/uninorm.py < raw_text.txt | \
    python unitok-4.0/unitok.py \
        unitok-4.0/configs/english.py > tokenized.vert
```

## Optional: Deduplicate
Remove duplicate paragraphs present in the vertical text.

```bash
onion < tokenized.vert > deduplicated.vert
cp deduplicated.vert corpus_input.vert
```

If you skip this step, use `tokenized.vert` as the input for the later corpus compilation step.

## Optional: Tag and Lemmatize

For a simpler workflow, you can continue with the `word` attribute. This is often acceptable for languages with relatively simple morphology. For richer morphology, it will be better to add lemmatization and before training the sense model, e.g. with TreeTagger.

The following steps use `word` to stay self-contained. If you have a tagger / lemmatizer available, this is the place to use it; add another column in the vertical and extend the corpus configuration file accordingly. Then, use this attribute instead of `word` in the following steps.

## Compile Corpus

Create a corpus configuration file, e.g. `corpus.conf`:

```bash
PATH "./compiled_corpus"
VERTICAL "./corpus_input.vert"
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
```

If your corpus is big, the positional attributes will need to use the MD\_MGD type, e.g.

```bash
ATTRIBUTE word {
    TYPE MD_MGD
}
```

and structures will need to use a wider storage type:

```bash
STRUCTURE p {
    TYPE map64
}
```


Compile the corpus with Manatee tools:

```bash
encodevert -c corpus.conf
mktokencov corpus.conf
```

or, compile the corpus using the tools provided by the `corp` crate:

```bash
encodevert -c corpus.conf
mkrev corpus.conf word
mkrev corpus.conf doc.date
mkrev corpus.conf doc.feed
mkrev corpus.conf doc.url
mkdynattr corpus.conf lc
mkdynattr corpus.conf doc.month
mktokencov corpus.conf
```

The tools provided by the `corp` crate are not as automated compared to `manatee`, but this allows for skipping some of the work to increase compilation speed. Only the `mkrev` commands are not strictly necessary for the trending sense detection, but they allow for easier inspection of the corpus.

The trend estimation below uses `doc.month` as the diachronic attribute. The methods have useful statistical power when there are 10+ epochs, so it might be better to use a different granularity for your particular corpus.

## Train the AdaGram Model

Train the model on the compiled corpus:

```bash
learn corpus.conf word model.adagram \
    --dim 64 --alpha 0.1 --window 10 --epochs 1 --prototypes 10 --threads 16
```

If your corpus has lemmatization, replace `word` with a lemmatized attribute.

## Prepare the List of Target Headwords

Obtain the list of top headwords by frequency. `lswl` emits `headword<TAB>frequency`, use only the first column.

```bash
lswl -l 100000 corpus.conf word > headwords_with_freqs.tsv
cut -f1 headwords_with_freqs.tsv > headwords.txt
```

You might need to decrease the cutoff specified by the `-l` parameter if your corpus is smaller/noisier, but this can also be done during subsequent steps.

## Compute Sense Frequencies

In this step, the diachronic frequencies of the word senses are calculated.

```bash
sensefreqs corpus.conf word doc.month model.adagram \
    --nthreads 16 < headwords.txt > sensed.tsv
```

Expected TSV columns:

```text
hw    epoch    s0    s1    ...    norm
```

Use the `--distrib` parameter to use soft-assignment of the word senses.

## Rank Trends

Apply trend estimation to the sense frequency distributions:

```bash
python rank_trends.py sensed.tsv \
    --method mk --norm en --out trends.tsv
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
    --input trends.tsv \
    --output filtered.tsv \
    --max-rank 30000 --max-p 0.01 --min-slope 0.01 \
    --pattern '.*'
```

Inspect a candidate headword with nearest neighbors:

```bash
echo "bank" | nearest model.adagram --compact
```

Inspect representative concordances:

```bash
echo "bank" | senseconc corpus.conf word word model.adagram \
    > concordances.tsv
```

Generate sense names with an LLM:

```bash
python name_senses_llm.py concordances.tsv > sense_names.tsv
```

`name_senses_llm.py` requires `OPENROUTER_API_KEY` to be set for LLM access using [OpenRouter](https://openrouter.ai)
