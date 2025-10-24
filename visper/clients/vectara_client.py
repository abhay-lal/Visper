try:
    from vectara_client import VectaraClient  # type: ignore
except Exception as _err:
    raise

__all__ = ["VectaraClient"]


