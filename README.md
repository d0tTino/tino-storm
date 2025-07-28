# tino-storm

STORM is a modular knowledge curation engine capable of generating structured
outlines and long-form articles from retrieved documents.  The project is now
split into two Python packages shipped from this repository:

- **`knowledge-storm`** – the core library implementing the STORM and
  Co‑STORM engines.
- **`tino-storm`** – a lightweight wrapper exposing a command line interface and
  a small FastAPI service.

Install the CLI and underlying library from PyPI:

```bash
pip install tino-storm
```

This command installs both the `tino-storm` wrapper and the
`knowledge-storm` package, along with all required dependencies.  Verify
the console script was installed with:

```bash
tino-storm --help
```

For development, install in editable mode to register the `tino-storm` command:

```bash
pip install -e .
# verify the script is on your $PATH
which tino-storm
```

## Command line usage

`tino-storm` provides a simple CLI.  The `run` sub-command executes a single
pipeline and optionally ingests the generated article into a named vault.  The
legacy `research` sub-command behaves the same without vault support.  The
`serve` sub-command starts the API service.

```bash
# Run a research task locally and save results under ./results
$ tino-storm run --topic "Quantum computing" --output-dir ./results --vault demo

# Legacy syntax
$ tino-storm research "Quantum computing" --output-dir ./results

# Start the API server
$ tino-storm serve --host 0.0.0.0 --port 8000

# Watch a directory for dropped files/URLs
$ tino-storm ingest --root ./vault
```

### The `ingest` command

`ingest` runs a small watcher that monitors a "vault" directory for new files.
Each first level subdirectory acts as the vault name. Dropped text files or
files ending in `.url`/`.urls` are parsed and the contents stored in a local
Chroma collection under `~/.tino_storm/chroma` (override with
`STORM_CHROMA_PATH`). The vault root defaults to `./research` but can be
customised with `--root` or the `STORM_VAULT_ROOT` environment variable.

#### Social manifests

The ingestion utilities include simple scrapers for Twitter, Reddit and 4chan
that produce JSON manifests.  Each item in a manifest should contain at least
`text` and `source` fields, for example:

```json
[
  {"text": "post text", "source": "https://twitter.com/..."},
  {"text": "another post", "source": "https://reddit.com/..."}
]
```

Drop such a `manifest.json` file inside your vault to have all entries ingested
as individual documents.

An `.arxiv` file with one identifier per line downloads each paper's metadata
and PDF text for ingestion.

A `.web` file should contain a JSON array of URLs. Each listed page will be
fetched and the extracted text ingested as a separate document.

#### Cross-vault search

Documents are stored in separate Chroma namespaces per vault.  Use
`search_vaults()` to query multiple vaults at once and aggregate the results
with Reciprocal Rank Fusion:

```python
from tino_storm.ingest import search_vaults

results = search_vaults("machine learning", ["science", "notes"])
```

### HTTP API

When running `tino-storm serve` the following POST endpoints become available:

- `/research` – execute the full pipeline and optionally ingest the result.
- `/outline` – run just the research and outline steps.
- `/draft` – generate a draft article without the polishing stage.
- `/ingest` – store arbitrary text in a named vault.

The first three endpoints accept a JSON body with `topic`, optional
`output_dir` and `vault` fields.  The `/ingest` endpoint expects `text`,
`vault` and an optional `source` identifying the origin of the text.

## Programmatic API

The CLI itself is a thin layer over the API defined in `tino_storm.api`.
The `run_research()` helper creates a default runner using the
`knowledge_storm` library and executes the pipeline.

```python
from tino_storm.api import run_research

run_research(topic="Quantum computing", output_dir="./results")
```

The lightweight `ResearchSkill` can also be used directly. When cloud access is
allowed you may tune its prompts using `optimize()`:

```python
from tino_storm.skills import ResearchSkill

skill = ResearchSkill(cloud_allowed=True)
skill.optimize()
result = skill("The Eiffel Tower")
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

## Encrypted vaults

You can optionally encrypt on-disk artefacts.  Create
`~/.tino_storm/config.yaml` with a passphrase:

```yaml
passphrase: "my secret"
```

You can also provide different keys per vault:

```yaml
passphrases:
  science: "pw1"
  notes: "pw2"
```

When configured, STORM uses this passphrase to encrypt JSON and pickle files
generated by `FileIOHelper` and the Chroma collections created by the ingest
command.

## Local-first defaults

By default STORM performs all work locally and writes artefacts to the
`--output-dir` directory.  Network calls to remote language models or search
services are disabled unless the environment variable `cloud_allowed=true` is
set, enabling cloud resources when desired.

## Local data encryption

When a passphrase is configured, dropped documents are encrypted before being
stored in the local Chroma database.  Add the following to
`~/.tino_storm/config.yaml`:

```yaml
passphrase: "my secret passphrase"
```

Existing users who set a passphrase for the first time should remove the old
`~/.tino_storm/chroma` directory and re-ingest any vault data so the documents
are encrypted.

To also encrypt any Parquet files created by Chroma, enable the
``encrypt_parquet`` flag:

```yaml
passphrase: "my secret passphrase"
encrypt_parquet: true
```

The watcher and ``search_vaults`` utility will transparently decrypt and re-
encrypt these files when running.

### Audit log

All external HTTP requests made by STORM are recorded in
``~/.tino_storm/audit.log``.  Each entry includes a timestamp, method and URL.

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
