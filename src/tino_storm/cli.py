import argparse
import uvicorn

from .api import app, run_research
from .ingest import start_watcher


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

    serve_p = subparsers.add_parser("serve", help="Launch API server")
    serve_p.add_argument("--host", default="0.0.0.0")
    serve_p.add_argument("--port", type=int, default=8000)

    ingest_p = subparsers.add_parser(
        "ingest", help="Watch a directory for dropped files"
    )
    ingest_p.add_argument("--root", help="Directory to watch")

    args = parser.parse_args(argv)

    if args.command == "research":
        run_research(
            topic=args.topic,
            output_dir=args.output_dir,
            do_research=not args.skip_research,
            do_generate_outline=not args.skip_outline,
            do_generate_article=not args.skip_article,
            do_polish_article=not args.skip_polish,
        )
    elif args.command == "serve":
        uvicorn.run(app, host=args.host, port=args.port)
    elif args.command == "ingest":
        start_watcher(root=args.root)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
