from datetime import datetime, timezone
from functools import lru_cache
from hashlib import sha256
from pathlib import Path

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
templates.env.globals["current_year"] = datetime.now(timezone.utc).year
templates.env.filters["money"] = lambda amount: f"{amount:,} ₴"

_STATIC_DIR = Path(__file__).parent / "static"


@lru_cache(maxsize=None)
def _asset_version(relative_path: str) -> str:
    """Short hash of a static file's actual bytes, used as a cache-busting
    query param so browsers can't keep serving a stale cached JS/CSS after a
    deploy. Deliberately content-based rather than mtime-based: on Vercel
    (and most CI/deploy pipelines that check out or repackage the repo) file
    mtimes get reset to a fixed build/checkout time, not the file's real
    last-edit time — an mtime-based version would then return the *same*
    value across every deploy regardless of what actually changed, letting a
    browser or edge cache serve stale CSS/JS indefinitely. Hashing the bytes
    directly is correct on every host. Cached per path since the file
    contents (and therefore the hash) can't change during a single running
    process — a new deploy is a new process, which starts with a cold cache. """
    return sha256((_STATIC_DIR / relative_path).read_bytes()).hexdigest()[:10]


templates.env.globals["asset_version"] = _asset_version
