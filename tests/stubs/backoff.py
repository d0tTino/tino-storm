__all__ = ["on_exception", "expo"]


def on_exception(*args, **kwargs):
    def decorator(func):
        return func

    return decorator


def expo(*args, **kwargs):
    return 0
