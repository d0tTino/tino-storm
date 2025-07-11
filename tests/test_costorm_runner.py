from knowledge_storm.collaborative_storm.engine import (
    CollaborativeStormLMConfigs,
    RunnerArgument,
    CoStormRunner,
)
from knowledge_storm.lm import LitellmModel
from knowledge_storm.logging_wrapper import LoggingWrapper


def _make_lm_config():
    cfg = CollaborativeStormLMConfigs()
    cfg.set_question_answering_lm(LitellmModel(model="qa"))
    cfg.set_discourse_manage_lm(LitellmModel(model="dm"))
    cfg.set_utterance_polishing_lm(LitellmModel(model="up"))
    cfg.set_warmstart_outline_gen_lm(LitellmModel(model="wo"))
    cfg.set_question_asking_lm(LitellmModel(model="ask"))
    cfg.set_knowledge_base_lm(LitellmModel(model="kb"))
    return cfg


def test_from_dict_loads_lm_config():
    lm_config = _make_lm_config()
    args = RunnerArgument(topic="t")
    runner = CoStormRunner(
        lm_config=lm_config,
        runner_argument=args,
        logging_wrapper=LoggingWrapper(lm_config),
    )

    data = {
        "runner_argument": args.to_dict(),
        "lm_config": {
            "question_answering_lm": {"model": "qa"},
            "discourse_manage_lm": {"model": "dm"},
            "utterance_polishing_lm": {"model": "up"},
            "warmstart_outline_gen_lm": {"model": "wo"},
            "question_asking_lm": {"model": "ask"},
            "knowledge_base_lm": {"model": "kb"},
        },
        "conversation_history": [],
        "warmstart_conv_archive": [],
        "experts": [],
        "knowledge_base": runner.knowledge_base.to_dict(),
    }

    new_runner = CoStormRunner.from_dict(data)
    assert new_runner.lm_config.question_answering_lm.model == "qa"
    assert new_runner.lm_config.discourse_manage_lm.model == "dm"
    assert new_runner.lm_config.knowledge_base_lm.model == "kb"
