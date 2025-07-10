# STORM

STORM is a modular pipeline for generating Wikipedia-style articles using external search results.

## Installation

Install the Python package from PyPI:

```bash
pip install knowledge-storm
```

## Import-based usage

The `tino_storm` package provides a thin wrapper around the original `knowledge_storm` modules.
A minimal example for generating an article is shown below.

```python
import os
from knowledge_storm import STORMWikiRunnerArguments, STORMWikiRunner, STORMWikiLMConfigs
from tino_storm.providers import get_llm, get_retriever

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

## CLI usage

A short command line interface is available in `examples/cli_example.py`:

```bash
python examples/cli_example.py "Quantum computing"
```

`OPENAI_API_KEY` and `BING_SEARCH_API_KEY` must be set in the environment (or provided via `secrets.toml`).


## Optional FastAPI mode

The file `examples/fastapi_example.py` exposes the pipeline over HTTP using FastAPI. Start it with:

```bash
uvicorn examples.fastapi_example:app --reload
```

Send a POST request to `/storm` with a JSON body such as `{"topic": "Neural networks"}` to receive the generated article.


## Migrating from `knowledge_storm`

The old `knowledge_storm` package is still included for backwards compatibility.
New code can import from `tino_storm` which re-exports the same functionality and adds convenience helpers.
Existing imports from `knowledge_storm` will continue to work but may be deprecated in the future.
