from __future__ import annotations

import argparse
from .config import StormConfig, create_retriever
from .storm import Storm


def make_config(args: argparse.Namespace | None = None) -> StormConfig:
    """Create a :class:`StormConfig` from command line ``args``.

    If ``args`` is ``None`` return :meth:`StormConfig.from_env`.
    """
    if args is None:
        return StormConfig.from_env()

    config = StormConfig.from_env()

    config.args.output_dir = args.output_dir
    config.args.max_conv_turn = args.max_conv_turn
    config.args.max_perspective = args.max_perspective
    config.args.search_top_k = args.search_top_k
    config.args.max_thread_num = args.max_thread_num
    config.args.retrieve_top_k = args.retrieve_top_k

    config.rm = create_retriever(args.retriever, config.args.search_top_k)

    return config


def _run_storm(args: argparse.Namespace) -> None:
    config = make_config(args)
    storm = Storm(config)
    topic = args.topic or input("Topic: ")
    article = storm.run_pipeline(topic, remove_duplicate=args.remove_duplicate)
    print(article)


def _run_outline(args: argparse.Namespace) -> None:
    config = make_config(args)
    storm = Storm(config)
    topic = args.topic or input("Topic: ")
    outline = storm.build_outline(topic)
    print(outline)


def _run_draft(args: argparse.Namespace) -> None:
    config = make_config(args)
    storm = Storm(config)
    draft = storm.generate_article()
    print(draft)


def _run_polish(args: argparse.Namespace) -> None:
    config = make_config(args)
    storm = Storm(config)
    article = storm.polish_article(remove_duplicate=args.remove_duplicate)
    print(article)


def _run_ingest(args: argparse.Namespace) -> None:
    from .ingest import watch_vault

    watch_vault(args.vault)


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    """Register arguments shared across commands."""

    parser.add_argument(
        "--output-dir", type=str, default="./results/cli", help="Directory for outputs"
    )
    parser.add_argument(
        "--max-thread-num", type=int, default=3, help="Maximum number of threads"
    )
    parser.add_argument(
        "--retriever",
        type=str,
        required=True,
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
    parser.add_argument("--max-conv-turn", type=int, default=3)
    parser.add_argument("--max-perspective", type=int, default=3)
    parser.add_argument("--search-top-k", type=int, default=3)
    parser.add_argument("--retrieve-top-k", type=int, default=3)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="tino-storm command line")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Run the STORM pipeline")
    _add_common_args(run_parser)
    run_parser.add_argument(
        "--remove-duplicate", action="store_true", help="Remove duplicate text"
    )
    run_parser.add_argument(
        "--topic",
        "-t",
        type=str,
        default=None,
        help="Topic to research. Prompted if omitted",
    )
    run_parser.set_defaults(func=_run_storm)

    outline_parser = sub.add_parser("outline", help="Generate an outline")
    _add_common_args(outline_parser)
    outline_parser.add_argument(
        "--topic",
        "-t",
        type=str,
        default=None,
        help="Topic to research. Prompted if omitted",
    )
    outline_parser.set_defaults(func=_run_outline)

    draft_parser = sub.add_parser("draft", help="Generate an article draft")
    _add_common_args(draft_parser)
    draft_parser.set_defaults(func=_run_draft)

    polish_parser = sub.add_parser("polish", help="Polish a draft article")
    _add_common_args(polish_parser)
    polish_parser.add_argument(
        "--remove-duplicate", action="store_true", help="Remove duplicate text"
    )
    polish_parser.set_defaults(func=_run_polish)

    ingest_parser = sub.add_parser("ingest", help="Ingest research files")
    ingest_parser.add_argument(
        "--vault", required=True, help="Name of the research vault"
    )
    ingest_parser.set_defaults(func=_run_ingest)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":  # pragma: no cover - manual invocation
    main()
