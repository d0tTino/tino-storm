# STORM

STORM is a modular pipeline for generating Wikipedia-style articles using external search results.

## Installation

Install the Python package from PyPI:

```bash
pip install tino-storm
```

### Optional extras

Install optional dependencies for different backends with:

```bash
pip install 'tino-storm[ollama]'           # Ollama backend
pip install 'tino-storm[fastapi]'          # FastAPI web server
pip install 'tino-storm[chroma]'           # Chroma-based ingestion
pip install 'tino-storm[ingest]'           # File watching for ingestion
pip install 'tino-storm[chroma,ingest]'    # Combined ingestion extras
pip install 'tino-storm[fastapi,ollama]'   # FastAPI with local LLM
pip install 'tino-storm[test]'             # Run the test suite
```

Alternatively, install the latest source version from this repository to get the
``tino-storm`` command:

```bash
pip install .
```

## Import-based usage

The `tino_storm` package provides a thin wrapper around the original `knowledge_storm` modules.
A minimal example for generating an article is shown below.


```python
import os
from knowledge_storm import (
    STORMWikiRunnerArguments,
    STORMWikiRunner,
    STORMWikiLMConfigs,
)
from tino_storm import get_llm, get_retriever

args = STORMWikiRunnerArguments()
lm_configs = STORMWikiLMConfigs()
Model = get_llm("openai")
Retriever = get_retriever("bing")

openai_lm = Model(model="gpt-3.5-turbo", api_key=os.getenv("OPENAI_API_KEY"))
lm_configs.set_conv_simulator_lm(openai_lm)
lm_configs.set_question_asker_lm(openai_lm)
lm_configs.set_outline_gen_lm(openai_lm)
lm_configs.set_article_gen_lm(openai_lm)

rm = Retriever(bing_search_api_key=os.getenv("BING_SEARCH_API_KEY"), k=args.search_top_k)
runner = STORMWikiRunner(args, lm_configs, rm)
article = runner.run(topic="Deep learning", do_research=True, do_generate_outline=True, do_generate_article=True)
print(article)
```

## Python API

The high-level :class:`~tino_storm.storm.Storm` class provides a minimal wrapper
around ``knowledge_storm``. Instantiate it with a :class:`StormConfig` and call
``run_pipeline``:

```python
from tino_storm import Storm, StormConfig

config = StormConfig.from_env()
article = Storm(config).run_pipeline(topic="Deep learning")
print(article)
```

## DSPy ResearchSkill

The package exposes a small `ResearchSkill` wrapper to compose the outline,
draft and polish modules. This can be used directly with DSPy tuning utilities.

```python
from tino_storm.dsp import ResearchSkill

skill = ResearchSkill(
    outline_lm=lm_configs.outline_gen_lm,
    draft_lm=lm_configs.article_gen_lm,
    polish_lm=lm_configs.article_polish_lm,
)
# `table` should be a StormInformationTable instance from the curation stage
article = skill("Deep learning", table)
```

### Tuning

Each research vault can include a small `eval.jsonl` file with evaluation topics. The
`ResearchSkill.tune()` method loads this data and evaluates the skill. This can be
used with simple stub LMs for local experiments:

```python
accuracy = skill.tune("example_vault")
print("Accuracy", accuracy)
```

## CLI usage

After installation, an entrypoint named ``tino-storm`` is available. Run the pipeline from the command line with:

```bash
tino-storm run --retriever bing --topic "Quantum computing"
```

Generate the outline only:

```bash
tino-storm outline --retriever bing --topic "Quantum computing"
```

Draft the article from a saved outline:

```bash
tino-storm draft --retriever bing
```

Polish an existing draft:

```bash
tino-storm polish --retriever bing --remove-duplicate
```

The command prints the generated article. Omit ``--topic`` to be prompted interactively or pass it to run non-interactively. Use ``--help`` to see all options.

To combine multiple search engines, prefix the retriever with ``rrf=`` and provide
a comma-separated list:

```bash
tino-storm run --retriever "rrf=bing,you" --topic "Quantum computing"
```

`OPENAI_API_KEY` and `BING_SEARCH_API_KEY` must be set in the environment (or provided via ``secrets.toml``).

## Configuration

Environment variables can be stored in a ``secrets.toml`` file placed next to your project:

```toml
OPENAI_API_KEY = "sk-..."
BING_SEARCH_API_KEY = "your-bing-key"
```

The CLI loads this file automatically so you don't need to export the variables yourself.

### ``StormConfig.from_env()``

You can programmatically create the same configuration using:

```python
from tino_storm import Storm, StormConfig

config = StormConfig.from_env()
article = Storm(config).run_pipeline("Quantum computing")
```

This helper reads the environment (or ``secrets.toml``) for API keys and optional variables like
``STORM_RETRIEVER`` or ``STORM_OUTPUT_DIR``. It then sets up the default LLMs and retriever so you
can immediately run a pipeline:


```python
article = Storm(config).run_pipeline("Quantum computing")
```

### Environment variables

The ``tino_storm.fastapi_app`` module also consults ``STORM_RETRIEVER`` to
select the search backend. Set this variable to one of the supported providers
or use ``rrf=`` to combine them, e.g. ``STORM_RETRIEVER=rrf=bing,you``.

Set ``STORM_CLOUD_ALLOWED=false`` to disable cloud-based LLM providers and
restrict the pipeline to local models like Ollama.

## Ingesting research data

Use the command below to monitor a vault directory for new research files and automatically index them:

```bash
tino-storm ingest --vault my_vault
```

This watches `research/my_vault/` for PDFs, `urls.txt`, and JSON dumps. Detected files are ingested with
LlamaIndex and stored in `~/.tino_storm/chroma/my_vault` using Chroma as the vector store. Install the optional
dependencies with:

```bash
pip install 'tino-storm[chroma,ingest]'
```

### Consuming events with UME

STORM writes JSON events to the directory specified by `STORM_EVENT_DIR`.
UME can monitor this folder and load the event data:

```python
import json
from pathlib import Path

for p in Path("events").glob("*.json"):
    event = json.loads(p.read_text())
    print(event["vault"], event["citation_hashes"])
```


## Optional FastAPI mode

You can integrate STORM into a web service using FastAPI. The repository ships with a small example app:

STORM pins the `httpx` dependency to `<0.28` for compatibility. When installing the FastAPI extra this constraint
is applied automatically:

```bash
uvicorn examples.fastapi_example:app --reload
```

This launches an HTTP API with ``/storm`` that accepts a JSON payload like
`{"topic": "Neural networks"}` and returns the generated article. The same logic is
available in ``tino_storm.fastapi_app`` for embedding in your own application.

### Calling the API

With the server running you can hit the endpoint using ``curl``:

```bash
curl -X POST http://127.0.0.1:8000/storm \
  -H "Content-Type: application/json" \
  -d '{"topic": "Neural networks"}'
```

Or from Python using ``requests``:

```python
import requests

resp = requests.post(
    "http://127.0.0.1:8000/storm",
    json={"topic": "Neural networks"},
)
print(resp.json()["article"])
```


## Migrating from `knowledge_storm`

The old `knowledge_storm` package is still included for backwards compatibility.
New code can import from `tino_storm` which re-exports the same functionality and adds convenience helpers.
Existing imports from `knowledge_storm` will continue to work but may be deprecated in the future.
