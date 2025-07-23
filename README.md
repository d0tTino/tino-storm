# tino-storm

STORM is a modular knowledge curation engine capable of generating structured
outlines and long-form articles from retrieved documents.  The project is now
split into two Python packages shipped from this repository:

- **`knowledge-storm`** – the core library implementing the STORM and
  Co‑STORM engines.
- **`tino-storm`** – a lightweight wrapper exposing a command line interface and
  a small FastAPI service.

Install both with:

```bash
pip install tino-storm  # installs knowledge-storm as a dependency

```

## Command line usage

`tino-storm` provides a simple CLI.  The `research` sub-command runs a single
pipeline and stores all outputs under the given directory.  The `serve`
sub-command starts the API service.

```bash
# Run a research task locally and save results under ./results
$ tino-storm research "Quantum computing" --output-dir ./results

# Start the API server
$ tino-storm serve --host 0.0.0.0 --port 8000
```

## Programmatic API

The CLI itself is a thin layer over the API defined in `tino_storm.api`.
The `run_research()` helper creates a default runner using the
`knowledge_storm` library and executes the pipeline.

```python
from tino_storm.api import run_research

run_research(topic="Quantum computing", output_dir="./results")
```

## Ingesting your own data

STORM can be grounded on a custom corpus by creating a Qdrant vector store and
using the `VectorRM` retriever.  The repository includes a helper script to build
the store from a CSV file:

```bash
python examples/storm_examples/run_storm_wiki_gpt_with_VectorRM.py \
    --csv-file-path docs.csv \
    --vector-db-mode offline \
    --offline-vector-db-dir ./vector_store \
    --output-dir ./results \
    --do-research --do-generate-outline \
    --do-generate-article --do-polish-article
```

## Local-first defaults

By default STORM performs all work locally and writes artefacts to the
`--output-dir` directory.  Network calls to remote language models or search
services are disabled unless the environment variable `cloud_allowed=true` is
set, enabling cloud resources when desired.

## Citation

If you use STORM or Co‑STORM in academic work, please cite the following:

```bibtex
@inproceedings{jiang-etal-2024-unknown,
  title={Into the Unknown Unknowns: Engaged Human Learning through Participation in Language Model Agent Conversations},
  author={Jiang, Yucheng and Shao, Yijia and Ma, Dekun and Semnani, Sina and Lam, Monica},
  booktitle={Proceedings of the 2024 Conference on Empirical Methods in Natural Language Processing},
  year={2024}
}

@inproceedings{shao-etal-2024-assisting,
  title={Assisting in Writing {W}ikipedia-like Articles From Scratch with Large Language Models},
  author={Shao, Yijia and Jiang, Yucheng and Kanell, Theodore and Xu, Peter and Khattab, Omar and Lam, Monica},
  booktitle={Proceedings of the 2024 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies},
  year={2024}
}
```
