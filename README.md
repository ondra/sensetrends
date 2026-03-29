# SenseTrends

Detect trending word senses in diachronic corpora.

The broader context is described in the thesis [_Automatic Detection of Word Sense Shift_](https://is.muni.cz/auth/th/tlymm/) and in the paper cited below. The basic idea is:

1. build a diachronic corpus with reliable timestamps
2. train an Adaptive Skip-gram model that induces multiple senses per headword
3. calculate per-sense frequencies across time
4. rank senses by the strength of their increase or decrease

Given a corpus and a trained [Adaptive Skip-gram](https://github.com/ondra/adagram) model, SenseTrends computes sense-by-epoch frequency distributions, estimates statistical trends, and produces ranked outputs that can be verified with concordances and nearest neighbors in the WSI model.

The thesis appendix contains the same overall pipeline, but some appendix command lines use older CLI syntax. The commands in this repository match the current binaries and scripts here.

For a concrete walkthrough, see [EXAMPLE.md](EXAMPLE.md).

## What Is In This Repository

This repository is the top layer of the trending sense detection pipeline. It contains:

- Python code for trend computation, filtering, and plotting
- bundled static Linux/x86_64 binaries in `bin/` for the tools which need compilation
- prebuilt Python extension modules: `slope.so`, `adagram.so`

The main components developed to achieve the goals of the thesis are:

| Tool | Repository | Purpose | Bundled here |
|------|------------|---------|--------------|
| **feed_fetcher** | [ondra/feed_fetcher](https://github.com/ondra/feed_fetcher) | Crawl RSS/Atom feeds and download article HTML | binaries |
| **corp** | [ondra/corp](https://github.com/ondra/corp) | Compile and query Manatee-compatible corpora | binaries |
| **adagram** | [ondra/adagram](https://github.com/ondra/adagram) | Train/query Adaptive Skip-gram models | binaries |
| **slope** | [ondra/slope](https://github.com/ondra/slope) | Trend-estimation library | |
| **pyslope** | [ondra/pyslope](https://github.com/ondra/pyslope) | Python bindings for trend estimation | `slope.so` |
| **pyadagram** | [ondra/pyadagram](https://github.com/ondra/pyadagram) | Python bindings for AdaGram queries | `adagram.so` |

## Dependencies

### Platform

The bundled binaries are prebuilt for Linux on `x86_64`. That is the primary supported environment for the pipeline, but any reasonable platform should work, I tried to avoid using any non-portable functionality.

### Python

Run the scripts from the repository root so Python can import the bundled `slope.so` and `adagram.so` modules.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Using the bundled binaries

The documentation assumes that the programs used are located on `PATH` and can be accessed directly. If you want to use the binaries bundled in this repository instead of installing the tools system-wide, export `PATH` in the current shell:

```bash
export PATH="$PWD/bin/feed_fetcher:$PWD/bin/corp:$PWD/bin/adagram:$PWD/bin/onion:$PATH"
```

### External tools needed for the full, from-web pipeline

This repository does not by itself replace the earlier preprocessing stages. For a full crawl-to-corpus workflow you still need:

- `dump.py` from [ondra/feed_fetcher](https://github.com/ondra/feed_fetcher)
- [jusText](https://corpus.tools/) for boilerplate removal
- `uninorm` and `unitok` from [corpus.tools](https://corpus.tools/)
- [Onion](https://corpus.tools/) for deduplication if you do not use the
  bundled binary
- optionally, a lemmatizer / PoS tagger for the target language

or,

- a diachronic corpus with a usable date attribute such as `doc.month`

## Minimal Ranking Workflow

Once you already have a compiled corpus and a trained AdaGram model, the steps to determine which senses are trending are:

### 1. Extract target headwords

First, choose the target headwords, which will be analyzed for change. This determines the top 100,000 lemposes by frequency:

```bash
lswl -l 100000 corpus.conf lempos > headwords_with_freqs.tsv
cut -f1 headwords_with_freqs.tsv > headwords.txt
```

`lswl` outputs `word<TAB>frequency`, so strip the frequency column before
feeding the list to `sensefreqs`.

### 2. Compute sense frequencies

In the next step, the frequency distribution of the senses over time is calculated. Use `doc.month` when the corpus exposes monthly bins.

```bash
sensefreqs corpus.conf lempos doc.month model.adagram \
    --nthreads 16 < headwords.txt > sensed.tsv
```

### 3. Rank sense trends

`rank_trends.py` accepts one or more TSV files produced by `sensefreqs`.

```bash
python rank_trends.py sensed.tsv --method mk --norm en --out trends.tsv
```

Method is `mk` for Mann-Kendall/Theil-Sen estimator, `lr` for Ordinary Least Squares.

Norm is `en` for epoch normalization, `gn` for global normalization, `sr` for sense-relative normalization.

### 4. Filter the ranking

`filter_trends_tsv.py` is a convenience script for filtering the TSV produced in the previous step.

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

## Repository Files

| File | Description |
|------|-------------|
| `rank_trends.py` | Rank sense trends from one or more TSV frequency files |
| `sensetrends_trends.py` | Normalization and slope / p-value computation |
| `plotword.py` | Sense-frequency visualization |
| `name_senses_llm.py` | LLM-based sense naming from concordances |
| `scripts/filter_trends_tsv.py` | Filter and sort ranked trend output |
| `Makefile.wl` | Local batch workflow for headword splitting, `sensefreqs`, and ranking |

## Notes

- Trend ranking needs a diachronic corpus with multiple epochs plus a trained
  sense model.
- Some helper and appendix-generation scripts in this checkout assume extra
  local files beyond the core ranking workflow.

## Citation

If you use SenseTrends in your research, please cite it as:

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
