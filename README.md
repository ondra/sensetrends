# SenseTrends

Automatic detection of trending word senses in diachronic monitor corpora.

Given a compiled diachronic corpus and a trained [Adaptive Skip-gram](https://github.com/ondra/adagram) model, SenseTrends computes per-sense frequency time series, estimates statistical trends, and ranks senses by the strength of their frequency change over time.

See [EXAMPLE.md](EXAMPLE.md) for a complete walkthrough of the pipeline.

## Dependencies

SenseTrends builds on several companion tools (prebuilt Linux/x86_64 binaries are included in this repository):

| Tool | Repository | Purpose |
|------|-----------|---------|
| **adagram** | [ondra/adagram](https://github.com/ondra/adagram) | Adaptive Skip-gram model training (`learn`) and querying (`nearest`, `senseconc`, `sensefreqs`, `desamb`) |
| **corp** | [ondra/corp](https://github.com/ondra/corp) | Manatee-compatible corpus compilation and access |
| **pyslope** | [ondra/pyslope](https://github.com/ondra/pyslope) | Statistical trend estimation (Mann-Kendall, linear regression) |
| **pyadagram** | [ondra/pyadagram](https://github.com/ondra/pyadagram) | Python bindings for adagram model queries |

External tools for corpus preparation (not included):
- [FeedFetcher](https://github.com/ondra/feed_fetcher) for web feed crawling
- [jusText](https://corpus.tools/) for boilerplate removal
- [Onion](https://corpus.tools/) for deduplication
- A lemmatizer/POS tagger for your target language

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Quick start

**1. Compute sense frequencies**

```bash
sensefreqs corpus.conf model.adagram lempos doc.month \
    --nthreads 16 < headwords.txt > sensed.tsv
```

**2. Rank trending senses**

```bash
python rank_trends.py sensed.tsv --method mk --norm en --out trends.tsv
```

**3. Filter results**

```bash
python scripts/filter_trends_tsv.py \
    --input trends.tsv --output filtered.tsv \
    --max-rank 30000 --max-p 0.01 --min-slope 0.01 \
    --pattern '.*'
```

**4. Plot a word**

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
| `rank_trends.py` | Rank sense trends from frequency files |
| `sensetrends_trends.py` | Core trend computation and normalization |
| `plotword.py` | Sense frequency visualization |
| `name_senses_llm.py` | LLM-based sense naming from concordances |
| `scripts/filter_trends_tsv.py` | Filter and sort trend output |

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
