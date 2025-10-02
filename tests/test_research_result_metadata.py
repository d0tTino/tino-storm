from __future__ import annotations

from tino_storm.retrieval import add_posteriors, reciprocal_rank_fusion, score_results
from tino_storm.search_result import ResearchResult, as_research_result


def test_as_research_result_preserves_optional_fields() -> None:
    data = {
        "url": "https://example.com",
        "snippets": ["example snippet"],
        "meta": {"title": "Example"},
        "summary": "Summary",
        "score": 1.23,
        "posterior": 0.42,
    }

    result = as_research_result(data)

    assert isinstance(result, ResearchResult)
    assert result.score == data["score"]
    assert result.posterior == data["posterior"]
    assert result.summary == data["summary"]


def test_retrieval_pipeline_retains_scores_and_posteriors() -> None:
    base_results = [
        {
            "url": "https://alpha.example",
            "snippets": ["alpha"],
            "meta": {"date": "2024-01-01", "citations": 1},
        },
        {
            "url": "https://beta.example",
            "snippets": ["beta"],
            "meta": {"date": "2023-12-15", "citations": 0},
        },
    ]

    ranking_one = score_results(base_results)
    ranking_two = score_results(list(reversed(base_results)))

    fused = reciprocal_rank_fusion([ranking_one, ranking_two], k=10)
    with_posteriors = add_posteriors(fused)
    results = [as_research_result(r) for r in with_posteriors]

    assert results, "Expected at least one fused result"
    results_by_url = {result.url: result for result in results}

    for original in base_results:
        result = results_by_url[original["url"]]
        assert result.meta == original["meta"]
        assert result.score is not None
        assert result.posterior is not None
