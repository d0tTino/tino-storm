__all__ = ["AutoTokenizer"]


class AutoTokenizer:
    @classmethod
    def from_pretrained(cls, *args, **kwargs):
        return cls()

    def __call__(self, text):
        return text
