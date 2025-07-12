"""STORM Wiki pipeline using local LLM via Ollama and VectorRM retrieval.

This example demonstrates running the entire STORM pipeline without external
APIs. All language model calls are served by an Ollama server and the
retrieval module reads from a Qdrant vector store via VectorRM.

Required environment variables:
    - QDRANT_API_KEY (only when using an online Qdrant instance)

You must have an Ollama server running with the desired model. Specify
--url, --port and --model accordingly. If the vector store does not yet exist
you can provide --csv-file-path to build it first.

Output will be structured as below
args.output_dir/
    topic_name/
        conversation_log.json
        raw_search_results.json
        direct_gen_outline.txt
        storm_gen_outline.txt
        url_to_info.json
        storm_gen_article.txt
        storm_gen_article_polished.txt
"""

import os
from argparse import ArgumentParser

from knowledge_storm import (
    STORMWikiRunnerArguments,
    STORMWikiRunner,
    STORMWikiLMConfigs,
)
from knowledge_storm.lm import OllamaClient
from knowledge_storm.rm import VectorRM
from knowledge_storm.utils import load_api_key, QdrantVectorStoreManager


def main(args):
    load_api_key(toml_file_path="secrets.toml")
    lm_configs = STORMWikiLMConfigs()
    ollama_kwargs = {
        "model": args.model,
        "port": args.port,
        "url": args.url,
        "stop": ("\n\n---",),
    }

    conv_simulator_lm = OllamaClient(max_tokens=500, **ollama_kwargs)
    question_asker_lm = OllamaClient(max_tokens=500, **ollama_kwargs)
    outline_gen_lm = OllamaClient(max_tokens=400, **ollama_kwargs)
    article_gen_lm = OllamaClient(max_tokens=700, **ollama_kwargs)
    article_polish_lm = OllamaClient(max_tokens=4000, **ollama_kwargs)

    lm_configs.set_conv_simulator_lm(conv_simulator_lm)
    lm_configs.set_question_asker_lm(question_asker_lm)
    lm_configs.set_outline_gen_lm(outline_gen_lm)
    lm_configs.set_article_gen_lm(article_gen_lm)
    lm_configs.set_article_polish_lm(article_polish_lm)

    engine_args = STORMWikiRunnerArguments(
        output_dir=args.output_dir,
        max_conv_turn=args.max_conv_turn,
        max_perspective=args.max_perspective,
        search_top_k=args.search_top_k,
        max_thread_num=args.max_thread_num,
    )

    if args.csv_file_path:
        kwargs = {
            "file_path": args.csv_file_path,
            "content_column": "content",
            "title_column": "title",
            "url_column": "url",
            "desc_column": "description",
            "batch_size": args.embed_batch_size,
            "vector_db_mode": args.vector_db_mode,
            "collection_name": args.collection_name,
            "embedding_model": args.embedding_model,
            "device": args.device,
        }
        if args.vector_db_mode == "offline":
            QdrantVectorStoreManager.create_or_update_vector_store(
                vector_store_path=args.offline_vector_db_dir, **kwargs
            )
        elif args.vector_db_mode == "online":
            QdrantVectorStoreManager.create_or_update_vector_store(
                url=args.online_vector_db_url,
                api_key=os.getenv("QDRANT_API_KEY"),
                **kwargs,
            )

    rm = VectorRM(
        collection_name=args.collection_name,
        embedding_model=args.embedding_model,
        device=args.device,
        k=engine_args.search_top_k,
    )
    if args.vector_db_mode == "offline":
        rm.init_offline_vector_db(vector_store_path=args.offline_vector_db_dir)
    elif args.vector_db_mode == "online":
        rm.init_online_vector_db(
            url=args.online_vector_db_url, api_key=os.getenv("QDRANT_API_KEY")
        )

    runner = STORMWikiRunner(engine_args, lm_configs, rm)

    topic = input("Topic: ")
    runner.run(
        topic=topic,
        do_research=args.do_research,
        do_generate_outline=args.do_generate_outline,
        do_generate_article=args.do_generate_article,
        do_polish_article=args.do_polish_article,
    )
    runner.post_run()
    runner.summary()


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--url", type=str, default="http://localhost", help="URL of the Ollama server."
    )
    parser.add_argument(
        "--port", type=int, default=11434, help="Port of the Ollama server."
    )
    parser.add_argument(
        "--model", type=str, default="llama3:latest", help="Model served by Ollama."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./results/full_local",
        help="Directory to store the outputs.",
    )
    parser.add_argument(
        "--max-thread-num",
        type=int,
        default=3,
        help="Maximum number of threads to use. The information seeking part and the article generation "
        "part can speed up by using multiple threads. Consider reducing it if keep getting "
        '"Exceed rate limit" error when calling LM API.',
    )
    parser.add_argument(
        "--collection-name",
        type=str,
        default="my_documents",
        help="The collection name for vector store.",
    )
    parser.add_argument(
        "--embedding_model",
        type=str,
        default="BAAI/bge-m3",
        help="Embedding model for VectorRM.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="mps",
        help="Device for running the retrieval model (mps, cuda, cpu, etc).",
    )
    parser.add_argument(
        "--vector-db-mode",
        type=str,
        choices=["offline", "online"],
        help="The mode of the Qdrant vector store (offline or online).",
    )
    parser.add_argument(
        "--offline-vector-db-dir",
        type=str,
        default="./vector_store",
        help="If offline mode, directory to store the vector store.",
    )
    parser.add_argument(
        "--online-vector-db-url",
        type=str,
        help="If online mode, URL of the Qdrant server.",
    )
    parser.add_argument(
        "--csv-file-path",
        type=str,
        default=None,
        help="Path to a corpus CSV used to build the vector store (optional).",
    )
    parser.add_argument(
        "--embed-batch-size",
        type=int,
        default=64,
        help="Batch size for embedding the documents in the csv file.",
    )
    parser.add_argument(
        "--do-research",
        action="store_true",
        help="Simulate conversation to research the topic.",
    )
    parser.add_argument(
        "--do-generate-outline",
        action="store_true",
        help="Generate an outline for the topic instead of loading the results.",
    )
    parser.add_argument(
        "--do-generate-article",
        action="store_true",
        help="Generate an article for the topic instead of loading the results.",
    )
    parser.add_argument(
        "--do-polish-article",
        action="store_true",
        help="Polish the article by adding a summarization section and optionally removing duplicate content.",
    )
    parser.add_argument(
        "--max-conv-turn",
        type=int,
        default=3,
        help="Maximum number of questions in conversational question asking.",
    )
    parser.add_argument(
        "--max-perspective",
        type=int,
        default=3,
        help="Maximum number of perspectives to consider in perspective-guided question asking.",
    )
    parser.add_argument(
        "--search-top-k",
        type=int,
        default=3,
        help="Top k search results to consider for each search query.",
    )
    parser.add_argument(
        "--retrieve-top-k",
        type=int,
        default=3,
        help="Top k collected references for each section title.",
    )
    parser.add_argument(
        "--remove-duplicate",
        action="store_true",
        help="Remove duplicate content from the article if True.",
    )
    main(parser.parse_args())
