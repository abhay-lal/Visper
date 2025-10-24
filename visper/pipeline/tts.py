try:
    from generate_tts import generate_tts  # type: ignore
except Exception as _err:
    raise

__all__ = ["generate_tts"]


