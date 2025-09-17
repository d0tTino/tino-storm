import argparse

from . import search_sync

start_watcher = None  # populated lazily for ingest command


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run STORM research pipelines")
    subparsers = parser.add_subparsers(dest="command", required=True)

    research_p = subparsers.add_parser("research", help="Run a single research task")
    research_p.add_argument("topic", help="Topic to research")
    research_p.add_argument(
        "--output-dir", default="./results", help="Directory for generated files"
    )
    research_p.add_argument(
        "--skip-research", action="store_true", help="Skip information retrieval"
    )
    research_p.add_argument(
        "--skip-outline", action="store_true", help="Skip outline generation"
    )
    research_p.add_argument(
        "--skip-article", action="store_true", help="Skip article generation"
    )
    research_p.add_argument(
        "--skip-polish", action="store_true", help="Skip article polishing"
    )

    run_p = subparsers.add_parser("run", help="Run a single research task")
    run_p.add_argument("--topic", required=True, help="Topic to research")
    run_p.add_argument("--vault", help="Vault to ingest results")
    run_p.add_argument(
        "--output-dir", default="./results", help="Directory for generated files"
    )
    run_p.add_argument(
        "--skip-research", action="store_true", help="Skip information retrieval"
    )
    run_p.add_argument(
        "--skip-outline", action="store_true", help="Skip outline generation"
    )
    run_p.add_argument(
        "--skip-article", action="store_true", help="Skip article generation"
    )
    run_p.add_argument(
        "--skip-polish", action="store_true", help="Skip article polishing"
    )

    search_p = subparsers.add_parser("search", help="Query ingested vaults")
    search_p.add_argument("--query", required=True, help="Search text")
    search_p.add_argument(
        "--vaults", required=True, help="Comma-separated list of vaults"
    )
    search_p.add_argument("--k-per-vault", type=int, default=5)
    search_p.add_argument("--rrf-k", type=int, default=60)

    serve_p = subparsers.add_parser("serve", help="Launch API server")
    serve_p.add_argument("--host", default="0.0.0.0")
    serve_p.add_argument("--port", type=int, default=8000)

    ingest_p = subparsers.add_parser(
        "ingest", help="Watch a directory for dropped files"
    )
    ingest_p.add_argument("--root", help="Directory to watch")
    ingest_p.add_argument("--twitter-limit", type=int, help="Max tweets per manifest")
    ingest_p.add_argument(
        "--reddit-limit", type=int, help="Max reddit posts per manifest"
    )
    ingest_p.add_argument(
        "--fourchan-limit", type=int, help="Max 4chan posts per manifest"
    )
    ingest_p.add_argument("--reddit-client-id")
    ingest_p.add_argument("--reddit-client-secret")

    args = parser.parse_args(argv)

    if args.command == "research":
        from .api import run_research

        run_research(
            topic=args.topic,
            output_dir=args.output_dir,
            do_research=not args.skip_research,
            do_generate_outline=not args.skip_outline,
            do_generate_article=not args.skip_article,
            do_polish_article=not args.skip_polish,
        )
    elif args.command == "run":
        from .api import run_research

        run_research(
            topic=args.topic,
            output_dir=args.output_dir,
            vault=args.vault,
            do_research=not args.skip_research,
            do_generate_outline=not args.skip_outline,
            do_generate_article=not args.skip_article,
            do_polish_article=not args.skip_polish,
        )
    elif args.command == "serve":
        try:
            import uvicorn
        except ImportError as e:  # pragma: no cover - optional dependency
            raise ImportError(
                "uvicorn is required to serve the API; install with 'tino-storm[research]'"
            ) from e

        from .api import app

        uvicorn.run(app, host=args.host, port=args.port)
    elif args.command == "ingest":
        global start_watcher
        if start_watcher is None:
            from .ingest import start_watcher as _start_watcher

            start_watcher = _start_watcher

        missing = getattr(start_watcher, "__tino_missing_dependency__", None)
        if missing:
            message = getattr(
                start_watcher,
                "__tino_missing_dependency_message__",
                "watchdog is required for ingestion features; install with 'tino-storm[research]'",
            )
            raise SystemExit(message)

        start_watcher(
            root=args.root,
            twitter_limit=args.twitter_limit,
            reddit_limit=args.reddit_limit,
            fourchan_limit=args.fourchan_limit,
            reddit_client_id=args.reddit_client_id,
            reddit_client_secret=args.reddit_client_secret,
        )
    elif args.command == "search":
        results = search_sync(
            args.query,
            args.vaults.split(","),
            k_per_vault=args.k_per_vault,
            rrf_k=args.rrf_k,
        )

        for item in results:
            snippet = item.snippets[0] if getattr(item, "snippets", None) else ""
            print(f"{item.url}: {snippet[:80]}")


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
