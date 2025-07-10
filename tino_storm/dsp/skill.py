from __future__ import annotations

from typing import Optional


class ResearchSkill:
    """High level skill that runs outline, draft and polish modules."""

    def __init__(
        self,
        outline_lm=None,
        draft_lm=None,
        polish_lm=None,
        *,
        outline_module=None,
        draft_module=None,
        polish_module=None,
    ):
        if outline_module is None:
            from knowledge_storm.storm_wiki.modules.outline_generation import (
                StormOutlineGenerationModule,
            )

            outline_module = StormOutlineGenerationModule(outline_gen_lm=outline_lm)
        if draft_module is None:
            from knowledge_storm.storm_wiki.modules.article_generation import (
                StormArticleGenerationModule,
            )

            draft_module = StormArticleGenerationModule(article_gen_lm=draft_lm)
        if polish_module is None:
            from knowledge_storm.storm_wiki.modules.article_polish import (
                StormArticlePolishingModule,
            )

            polish_module = StormArticlePolishingModule(
                article_gen_lm=draft_lm, article_polish_lm=polish_lm
            )

        self.outline_module = outline_module
        self.draft_module = draft_module
        self.polish_module = polish_module

    def __call__(
        self,
        topic: str,
        information_table,
        *,
        remove_duplicate: bool = False,
        callback_handler: Optional[object] = None,
    ):
        outline = self.outline_module.generate_outline(
            topic=topic,
            information_table=information_table,
            callback_handler=callback_handler,
        )
        draft = self.draft_module.generate_article(
            topic=topic,
            information_table=information_table,
            article_with_outline=outline,
            callback_handler=callback_handler,
        )
        article = self.polish_module.polish_article(
            topic=topic, draft_article=draft, remove_duplicate=remove_duplicate
        )
        return article
