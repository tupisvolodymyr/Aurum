from datetime import datetime, timezone
from pathlib import Path

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
templates.env.globals["current_year"] = datetime.now(timezone.utc).year
templates.env.filters["money"] = lambda amount: f"{amount:,} ₴"

_STATIC_DIR = Path(__file__).parent / "static"


def _asset_version(relative_path: str) -> int:
    """mtime of a static file, used as a cache-busting query param so
    browsers can't keep serving a stale cached JS/CSS after a deploy."""
    return int((_STATIC_DIR / relative_path).stat().st_mtime)


templates.env.globals["asset_version"] = _asset_version
