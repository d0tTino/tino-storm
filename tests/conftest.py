import os
import sys
import types
import builtins
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
    "numpy",
    "cryptography",
    "requests",
    "pytz",
    "watchdog",
    "yaml",
    "chromadb",
    "uvicorn",
    "fastapi",
    "pydantic",
    "snscrape",
    "snscrape.modules",
    "snscrape.modules.twitter",
    "PIL",
    "PIL.Image",
    "pytesseract",
    "praw",
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

            class HTTPError(Exception):
                pass

            class Client:
                def __init__(self, *a, **k):
                    pass

                def get(self, *a, **k):
                    return types.SimpleNamespace(status_code=200, content=b"")

            def get(*a, **k):
                return Client().get(*a, **k)

            module.Client = Client
            module.HTTPError = HTTPError
            module.get = get
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

            def _dot(u, v):
                return sum(x * y for x, y in zip(u, v))

            def _norm(v):
                return sum(x * x for x in v) ** 0.5

            def cosine_similarity(a, b):
                result = []
                for vec_a in a:
                    row = []
                    for vec_b in b:
                        denom = (_norm(vec_a) * _norm(vec_b)) + 1e-8
                        row.append(_dot(vec_a, vec_b) / denom)
                    result.append(row)
                return result

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
        elif _missing == "numpy":
            numpy_mod = types.ModuleType("numpy")

            def array(obj):
                return list(obj)

            def argsort(seq):
                return sorted(range(len(seq)), key=lambda i: seq[i])

            def max(arr, axis=None):
                if axis is None:
                    return builtins.max(arr)
                if axis == 1:
                    return [builtins.max(row) for row in arr]
                return builtins.max(arr)

            def clip(arr, a_min, a_max):
                return [min(max(x, a_min), a_max) for x in arr]

            def where(cond, x, y):
                return [xi if ci else yi for ci, xi, yi in zip(cond, x, y)]

            class ndarray(list):
                @property
                def size(self):
                    if not self:
                        return 0
                    if isinstance(self[0], list):
                        return len(self) * len(self[0])
                    return len(self)

                def __getitem__(self, idx):
                    if isinstance(idx, list):
                        return ndarray([super().__getitem__(i) for i in idx])
                    return super().__getitem__(idx)

            numpy_mod.array = lambda obj: ndarray(obj)
            numpy_mod.argsort = argsort
            numpy_mod.max = max
            numpy_mod.clip = clip
            numpy_mod.where = where
            numpy_mod.ndarray = ndarray
            sys.modules["numpy"] = numpy_mod
            module = numpy_mod
        elif _missing == "cryptography":
            crypto_mod = types.ModuleType("cryptography")
            fernet_mod = types.ModuleType("cryptography.fernet")
            hazmat_mod = types.ModuleType("cryptography.hazmat")
            backends_mod = types.ModuleType("cryptography.hazmat.backends")
            primitives_mod = types.ModuleType("cryptography.hazmat.primitives")
            hashes_mod = types.ModuleType("cryptography.hazmat.primitives.hashes")
            kdf_mod = types.ModuleType("cryptography.hazmat.primitives.kdf")
            pbkdf2_mod = types.ModuleType("cryptography.hazmat.primitives.kdf.pbkdf2")

            class Fernet:
                def __init__(self, key: bytes):
                    self.key = key

                def encrypt(self, data: bytes) -> bytes:
                    return b"enc:" + data

                def decrypt(self, token: bytes) -> bytes:
                    if token.startswith(b"enc:"):
                        return token[4:]
                    return token

            def default_backend():
                return None

            class SHA256:
                pass

            class PBKDF2HMAC:
                def __init__(self, algorithm, length, salt, iterations, backend=None):
                    self.length = length
                    self.salt = salt
                    self.iterations = iterations

                def derive(self, data: bytes) -> bytes:
                    import hashlib

                    return hashlib.pbkdf2_hmac(
                        "sha256", data, self.salt, self.iterations, dklen=self.length
                    )

            fernet_mod.Fernet = Fernet
            backends_mod.default_backend = default_backend
            hashes_mod.SHA256 = SHA256
            pbkdf2_mod.PBKDF2HMAC = PBKDF2HMAC
            kdf_mod.pbkdf2 = pbkdf2_mod
            primitives_mod.hashes = hashes_mod
            primitives_mod.kdf = kdf_mod
            hazmat_mod.backends = backends_mod
            hazmat_mod.primitives = primitives_mod
            crypto_mod.fernet = fernet_mod
            crypto_mod.hazmat = hazmat_mod
            module = crypto_mod
            sys.modules["cryptography.fernet"] = fernet_mod
            sys.modules["cryptography.hazmat"] = hazmat_mod
            sys.modules["cryptography.hazmat.backends"] = backends_mod
            sys.modules["cryptography.hazmat.primitives"] = primitives_mod
            sys.modules["cryptography.hazmat.primitives.hashes"] = hashes_mod
            sys.modules["cryptography.hazmat.primitives.kdf"] = kdf_mod
            sys.modules["cryptography.hazmat.primitives.kdf.pbkdf2"] = pbkdf2_mod
        elif _missing == "requests":

            def _resp(*a, **k):
                return types.SimpleNamespace(
                    status_code=200, json=lambda: {}, text="", content=b""
                )

            class Session:
                def get(self, *a, **k):
                    return _resp()

                def post(self, *a, **k):
                    return _resp()

            module.get = lambda *a, **k: _resp()
            module.post = lambda *a, **k: _resp()
            module.Session = Session
        elif _missing == "pytz":

            class _TZ:
                def __init__(self, name: str):
                    self.name = name

                def localize(self, dt):
                    return dt

            module.timezone = lambda name: _TZ(name)
            module.utc = _TZ("UTC")
        elif _missing == "watchdog":
            observers_mod = types.ModuleType("watchdog.observers")
            events_mod = types.ModuleType("watchdog.events")

            class FileSystemEventHandler:
                pass

            class Observer:
                def schedule(self, *a, **k):
                    pass

                def start(self):
                    pass

                def stop(self):
                    pass

                def join(self, *a, **k):
                    pass

            observers_mod.Observer = Observer
            events_mod.FileSystemEventHandler = FileSystemEventHandler
            module.observers = observers_mod
            module.events = events_mod
            sys.modules["watchdog.observers"] = observers_mod
            sys.modules["watchdog.events"] = events_mod
        elif _missing == "yaml":

            def safe_load(*a, **k):
                return {}

            def dump(data, *a, **k):
                return ""

            module.safe_load = safe_load
            module.dump = dump
        elif _missing == "chromadb":
            chroma_mod = types.ModuleType("chromadb")
            api_mod = types.ModuleType("chromadb.api")
            config_mod = types.ModuleType("chromadb.config")

            class DummyCollection:
                def __init__(self):
                    self.docs = []
                    self.ids = []

                def add(self, documents=None, ids=None, **kw):
                    if documents:
                        self.docs.extend(documents)
                    if ids:
                        self.ids.extend(ids)

                def query(self, **kw):
                    return {"documents": [self.docs]}

            class PersistentClient:
                def __init__(self, *a, **k):
                    self.collections = {}

                def get_or_create_collection(self, name, **kw):
                    if name not in self.collections:
                        self.collections[name] = DummyCollection()
                    return self.collections[name]

            api_mod.Collection = DummyCollection

            class Settings:
                def __init__(self, *a, **k):
                    pass

            config_mod.Settings = Settings
            chroma_mod.PersistentClient = PersistentClient
            sys.modules["chromadb.api"] = api_mod
            sys.modules["chromadb.config"] = config_mod
            module = chroma_mod
        elif _missing == "yaml":

            def safe_load(*a, **k):
                return {}

            def dump(data, *a, **k):
                return ""

            module.safe_load = safe_load
            module.dump = dump
        elif _missing == "uvicorn":

            class Config:
                def __init__(self, *a, **k):
                    pass

            class Server:
                def __init__(self, *a, **k):
                    pass

                def run(self):
                    pass

            module.Config = Config
            module.Server = Server
        elif _missing == "fastapi":

            class FastAPI:
                def __init__(self, *a, **k):
                    pass

                def get(self, *a, **k):
                    def decorator(fn):
                        return fn

                    return decorator

                def post(self, *a, **k):
                    def decorator(fn):
                        return fn

                    return decorator

            module.FastAPI = FastAPI
        elif _missing == "pydantic":

            class BaseModel:
                def __init__(self, **data):
                    for k, v in data.items():
                        setattr(self, k, v)

                model_config = types.SimpleNamespace()

            module.BaseModel = BaseModel
        elif _missing.startswith("snscrape"):
            if _missing in ("snscrape", "snscrape.modules", "snscrape.modules.twitter"):
                twitter_mod = types.ModuleType("snscrape.modules.twitter")

                class TwitterSearchScraper:
                    def __init__(self, *a, **k):
                        pass

                    def get_items(self):
                        return []

                twitter_mod.TwitterSearchScraper = TwitterSearchScraper
                sys.modules["snscrape.modules.twitter"] = twitter_mod
                if "snscrape.modules" not in sys.modules:
                    modules_mod = types.ModuleType("snscrape.modules")
                    sys.modules["snscrape.modules"] = modules_mod
                else:
                    modules_mod = sys.modules["snscrape.modules"]
                modules_mod.twitter = twitter_mod
                if "snscrape" not in sys.modules:
                    sns_mod = types.ModuleType("snscrape")
                    sys.modules["snscrape"] = sns_mod
                else:
                    sns_mod = sys.modules["snscrape"]
                sns_mod.modules = modules_mod
                if _missing == "snscrape.modules.twitter":
                    module = twitter_mod
                elif _missing == "snscrape.modules":
                    module = modules_mod
                else:
                    module = sns_mod
        elif _missing == "PIL" or _missing == "PIL.Image":
            pil_mod = types.ModuleType("PIL")
            image_mod = types.ModuleType("PIL.Image")

            class Image:
                def __init__(self, *a, **k):
                    pass

                @staticmethod
                def open(*a, **k):
                    return Image()

            image_mod.Image = Image
            pil_mod.Image = Image
            sys.modules.setdefault("PIL", pil_mod)
            sys.modules.setdefault("PIL.Image", image_mod)
            module = pil_mod if _missing == "PIL" else image_mod
        elif _missing == "pytesseract":
            pytesseract_mod = types.ModuleType("pytesseract")

            def image_to_string(*a, **k):
                return ""

            pytesseract_mod.image_to_string = image_to_string
            module = pytesseract_mod
        elif _missing == "praw":
            praw_mod = types.ModuleType("praw")

            class Reddit:
                def __init__(self, *a, **k):
                    pass

                class Subreddit:
                    def __init__(self, *a, **k):
                        pass

                    def search(self, *a, **k):
                        return []

                def subreddit(self, *a, **k):
                    return Reddit.Subreddit()

            praw_mod.Reddit = Reddit
            module = praw_mod
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

    def fake_post(*args, **kwargs):
        return DummyResponse({}, "")

    monkeypatch.setattr("requests.get", fake_get, raising=False)
    monkeypatch.setattr("requests.post", fake_post, raising=False)
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
