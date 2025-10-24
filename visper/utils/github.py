try:
    from utils import parse_github_url  # type: ignore
except Exception as _err:
    raise

__all__ = ["parse_github_url"]


