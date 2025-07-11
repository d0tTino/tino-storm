from __future__ import annotations

import argparse


from .config import StormConfig
from .storm import Storm


def make_config(args: argparse.Namespace) -> StormConfig:
    """Create a :class:`StormConfig` from command line ``args``."""
    return StormConfig.from_env(
        retriever=args.retriever,
        output_dir=args.output_dir,
        max_conv_turn=args.max_conv_turn,
        max_perspective=args.max_perspective,
        search_top_k=args.search_top_k,
        retrieve_top_k=args.retrieve_top_k,
        max_thread_num=args.max_thread_num,
    )


def _run_storm(args: argparse.Namespace) -> None:
    config = make_config(args)
    storm = Storm(config)
    topic = input("Topic: ")
    article = storm.run_pipeline(topic, remove_duplicate=args.remove_duplicate)
    print(article)


def _run_ingest(args: argparse.Namespace) -> None:
    from .ingest import watch_vault

    watch_vault(args.vault)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="tino-storm command line")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Run the STORM pipeline")
    run_parser.add_argument(
        "--output-dir", type=str, default="./results/cli", help="Directory for outputs"
    )
    run_parser.add_argument(
        "--max-thread-num", type=int, default=3, help="Maximum number of threads"
    )
    run_parser.add_argument(
        "--retriever",
        type=str,
        required=False,
        choices=[
            "bing",
            "you",
            "brave",
            "serper",
            "duckduckgo",
            "tavily",
            "searxng",
            "azure_ai_search",
        ],
        help="Search engine to use",
    )
    run_parser.add_argument("--max-conv-turn", type=int, default=3)
    run_parser.add_argument("--max-perspective", type=int, default=3)
    run_parser.add_argument("--search-top-k", type=int, default=3)
    run_parser.add_argument("--retrieve-top-k", type=int, default=3)
    run_parser.add_argument(
        "--remove-duplicate", action="store_true", help="Remove duplicate text"
    )
    run_parser.set_defaults(func=_run_storm)

    ingest_parser = sub.add_parser("ingest", help="Ingest research files")
    ingest_parser.add_argument(
        "--vault", required=True, help="Name of the research vault"
    )
    ingest_parser.set_defaults(func=_run_ingest)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":  # pragma: no cover - manual invocation
    main()
