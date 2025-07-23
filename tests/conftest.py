import os
import sys
import types
import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
SRC_DIR = os.path.join(ROOT_DIR, "src")
if os.path.isdir(SRC_DIR) and SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Provide lightweight stubs for internal modules imported during tests
if "tino_storm.encoder" not in sys.modules:
    enc_mod = types.ModuleType("tino_storm.encoder")

    class Encoder:
        def __init__(self, *a, **k):
            pass

    enc_mod.Encoder = Encoder
    sys.modules["tino_storm.encoder"] = enc_mod

# Stub optional dependencies so tests do not require heavy installs
for _missing in [
    "langchain_text_splitters",
    "trafilatura",
    "transformers",
    "regex",
    "bs4",
    "httpx",
    "toml",
    "tqdm",
    "backoff",
    "sentence_transformers",
    "ujson",
    "sklearn",
    "qdrant_client",
    "pandas",
]:
    if _missing not in sys.modules:
        module = types.ModuleType(_missing)
        if _missing == "langchain_text_splitters":

            class _DummySplitter:
                def __init__(self, *a, **k):
                    pass

                def split_documents(self, docs):
                    return docs

            module.RecursiveCharacterTextSplitter = _DummySplitter
        elif _missing == "trafilatura":

            def extract(*_args, **_kwargs):
                return ""

            module.extract = extract
        elif _missing == "transformers":

            class _DummyTokenizer:
                @classmethod
                def from_pretrained(cls, *a, **k):
                    return cls()

            module.AutoTokenizer = _DummyTokenizer
        elif _missing == "regex":
            module.sub = lambda *a, **k: ""
            module.findall = lambda *a, **k: []
        elif _missing == "bs4":

            class BeautifulSoup:
                def __init__(self, *a, **k):
                    pass

            module.BeautifulSoup = BeautifulSoup
        elif _missing == "httpx":

            class Client:
                def __init__(self, *a, **k):
                    pass

                def get(self, *a, **k):
                    return types.SimpleNamespace(status_code=200, content=b"")

            module.Client = Client
        elif _missing == "toml":

            def load(*a, **k):
                return {}

            module.load = load
        elif _missing == "tqdm":

            def tqdm(iterable, *a, **k):
                return list(iterable)

            module.tqdm = tqdm
        elif _missing == "backoff":

            def on_exception(*a, **k):
                def wrapper(fn):
                    return fn

                return wrapper

            def expo(*a, **k):
                return 0

            module.on_exception = on_exception
            module.expo = expo
        elif _missing == "sentence_transformers":

            class SentenceTransformer:
                def __init__(self, *a, **k):
                    pass

                def encode(self, data):
                    return [0] * len(data)

            module.SentenceTransformer = SentenceTransformer
        elif _missing == "ujson":

            def loads(s):
                return {}

            def dumps(obj):
                return "{}"

            module.loads = loads
            module.dumps = dumps
        elif _missing == "sklearn":
            sklearn_mod = types.ModuleType("sklearn")
            metrics_mod = types.ModuleType("sklearn.metrics")
            pairwise_mod = types.ModuleType("sklearn.metrics.pairwise")

            import numpy as _np

            def cosine_similarity(a, b):
                a = _np.array(a)
                b = _np.array(b)
                a_norm = a / (_np.linalg.norm(a, axis=1, keepdims=True) + 1e-8)
                b_norm = b / (_np.linalg.norm(b, axis=1, keepdims=True) + 1e-8)
                return a_norm @ b_norm.T

            pairwise_mod.cosine_similarity = cosine_similarity
            metrics_mod.pairwise = pairwise_mod
            sklearn_mod.metrics = metrics_mod
            sys.modules["sklearn.metrics"] = metrics_mod
            sys.modules["sklearn.metrics.pairwise"] = pairwise_mod
            module = sklearn_mod
            module.metrics = metrics_mod
        elif _missing == "qdrant_client":
            qdrant_mod = types.ModuleType("qdrant_client")

            http_mod = types.ModuleType("qdrant_client.http")
            models_mod = types.ModuleType("qdrant_client.http.models")

            class _Dummy:
                pass

            class Filter:
                def __init__(self, *a, **k):
                    pass

            class FieldCondition:
                def __init__(self, *a, **k):
                    pass

            class MatchValue:
                def __init__(self, *a, **k):
                    pass

            models_mod.Filter = Filter
            models_mod.FieldCondition = FieldCondition
            models_mod.MatchValue = MatchValue

            http_mod.models = models_mod
            qdrant_mod.http = http_mod
            sys.modules["qdrant_client.http"] = http_mod
            sys.modules["qdrant_client.http.models"] = models_mod

            class Document:
                def __init__(self, page_content="", metadata=None):
                    self.page_content = page_content
                    self.metadata = metadata or {}

            class QdrantClient:
                def __init__(self, *a, **k):
                    self._data = []

                def close(self):
                    pass

                def scroll(self, *a, **k):
                    return [], None

            qdrant_mod.Document = Document
            qdrant_mod.QdrantClient = QdrantClient
            module = qdrant_mod
        elif _missing == "pandas":
            pandas_mod = types.ModuleType("pandas")

            class DataFrame(list):
                def __init__(self, data):
                    list.__init__(self, data)
                    self.columns = list(data[0].keys()) if data else []

                def to_dict(self, orient="records"):
                    return list(self)

            def read_csv(path):
                import csv

                with open(path, "r", newline="") as f:
                    reader = csv.DictReader(f)
                    return DataFrame([row for row in reader])

            pandas_mod.read_csv = read_csv
            pandas_mod.DataFrame = DataFrame
            module = pandas_mod
        sys.modules[_missing] = module

for _missing in ["litellm", "openai", "dspy", "dsp"]:
    if _missing not in sys.modules:
        module = types.ModuleType(_missing)
        if _missing == "dspy" or _missing == "dsp":

            dsp_sub = types.ModuleType("dsp")

            class LM:
                pass

            class HFModel:
                pass

            class OpenAI:
                def __init__(self, *a, **k):
                    pass

            class OllamaLocal:
                def __init__(self, *a, **k):
                    pass

            class OllamaClient:
                def __init__(self, *a, **k):
                    pass

            class HFClientTGI:
                def __init__(self, *a, **k):
                    pass

            class Together:
                pass

            class Retrieve:
                def __init__(self, k=3, **kwargs):
                    self.k = k

                def __call__(self, *a, **k):
                    return []

            class Signature:
                pass

            class Module:
                def __init__(self, *a, **k):
                    pass

            class Predict:
                def __init__(self, *a, **k):
                    self.result = types.SimpleNamespace()

                def __call__(self, *a, **k):
                    return self.result

            class Prediction:
                def __init__(self, **kwargs):
                    self.__dict__.update(kwargs)

            class ChainOfThought(Predict):
                pass

            class InputField:
                def __init__(self, *a, **k):
                    pass

            class OutputField(InputField):
                pass

            class settings:
                class context:
                    def __init__(self, **kw):
                        pass

                    def __enter__(self):
                        return None

                    def __exit__(self, *a):
                        return False

            ERRORS = Exception

            def backoff_hdlr(*a, **k):
                pass

            def giveup_hdlr(*a, **k):
                return False

            dsp_sub.LM = LM
            dsp_sub.HFModel = HFModel
            dsp_sub.OpenAI = OpenAI
            dsp_sub.OllamaLocal = OllamaLocal
            dsp_sub.OllamaClient = OllamaClient
            dsp_sub.HFClientTGI = HFClientTGI
            dsp_sub.Together = Together
            dsp_sub.Retrieve = Retrieve
            dsp_sub.Signature = Signature
            dsp_sub.Module = Module
            dsp_sub.Predict = Predict
            dsp_sub.Prediction = Prediction
            dsp_sub.ChainOfThought = ChainOfThought
            dsp_sub.InputField = InputField
            dsp_sub.OutputField = OutputField
            dsp_sub.settings = settings
            dsp_sub.ERRORS = ERRORS
            dsp_sub.backoff_hdlr = backoff_hdlr
            dsp_sub.giveup_hdlr = giveup_hdlr
            dsp_sub.modules = types.ModuleType("modules")
            dsp_sub.modules.hf = types.ModuleType("hf")
            dsp_sub.modules.hf_client = types.ModuleType("hf_client")
            dsp_sub.modules.lm = types.ModuleType("lm")
            dsp_sub.modules.lm.LM = LM

            def openai_to_hf(*a, **k):
                pass

            def send_hftgi_request_v01_wrapped(*a, **k):
                pass

            dsp_sub.modules.hf.openai_to_hf = openai_to_hf
            dsp_sub.modules.hf_client.send_hftgi_request_v01_wrapped = (
                send_hftgi_request_v01_wrapped
            )
            sys.modules["dsp.modules"] = dsp_sub.modules
            sys.modules["dsp.modules.hf"] = dsp_sub.modules.hf
            sys.modules["dsp.modules.hf_client"] = dsp_sub.modules.hf_client
            module.dsp = dsp_sub
            module.Retrieve = Retrieve
            module.LM = LM
            module.HFModel = HFModel
            module.OpenAI = OpenAI
            module.OllamaLocal = OllamaLocal
            module.OllamaClient = OllamaClient
            module.HFClientTGI = HFClientTGI
            module.Together = Together
            module.Signature = Signature
            module.Module = Module
            module.Predict = Predict
            module.Prediction = Prediction
            module.ChainOfThought = ChainOfThought
            module.InputField = InputField
            module.OutputField = OutputField
            module.settings = settings
            module.ERRORS = ERRORS
            module.backoff_hdlr = backoff_hdlr
            module.giveup_hdlr = giveup_hdlr
            module.OpenAI = OpenAI
            module.OllamaLocal = OllamaLocal
            module.modules = types.ModuleType("modules")
            module.modules.hf = types.ModuleType("hf")
            module.modules.hf_client = types.ModuleType("hf_client")
            module.modules.lm = types.ModuleType("lm")
            module.modules.lm.LM = LM
            module.modules.hf.openai_to_hf = openai_to_hf
            module.modules.hf_client.send_hftgi_request_v01_wrapped = (
                send_hftgi_request_v01_wrapped
            )
        elif _missing == "openai":

            class OpenAI:
                pass

            class AzureOpenAI:
                pass

            module.OpenAI = OpenAI
            module.AzureOpenAI = AzureOpenAI
        elif _missing == "litellm":
            caching_mod = types.ModuleType("litellm.caching")
            caching_sub = types.ModuleType("litellm.caching.caching")
            caching_sub.Cache = lambda *a, **k: None
            caching_mod.caching = caching_sub
            sys.modules["litellm.caching"] = caching_mod
            sys.modules["litellm.caching.caching"] = caching_sub
            module.caching = caching_mod
        sys.modules[_missing] = module


class DummyResponse:
    def __init__(self, data=None, text=""):
        self._data = data or {}
        self.status_code = 200
        self._text = text

    def json(self):
        return self._data

    @property
    def content(self):
        return self._text.encode("utf-8")


@pytest.fixture(autouse=True)
def mock_requests(monkeypatch):
    def fake_get(*args, **kwargs):
        # Simulate a generic search response
        return DummyResponse({"webPages": {"value": []}, "hits": []}, "<html></html>")

    monkeypatch.setattr("requests.get", fake_get)
    return fake_get


@pytest.fixture(autouse=True)
def mock_file_watcher(monkeypatch):
    try:
        import watchdog.observers  # noqa: F401
    except Exception:
        module = types.ModuleType("watchdog.observers")
        parent = types.ModuleType("watchdog")
        parent.observers = module
        sys.modules["watchdog"] = parent
        sys.modules["watchdog.observers"] = module

    class DummyObserver:
        def schedule(self, *a, **k):
            pass

        def start(self):
            pass

        def stop(self):
            pass

        def join(self, *a, **k):
            pass

    monkeypatch.setattr(
        "watchdog.observers.Observer", lambda *a, **k: DummyObserver(), raising=False
    )


@pytest.fixture(autouse=True)
def set_bing_api_key(monkeypatch):
    monkeypatch.setenv("BING_SEARCH_API_KEY", "dummy")
