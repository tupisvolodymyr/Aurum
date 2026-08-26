def safe_next_path(path: str | None) -> str | None:
    """Only accept same-site relative paths as a post-login redirect target.

    Rejects protocol-relative ("//evil.com") and absolute URLs ("https://...")
    so a crafted `next` query param can't be used for an open redirect.
    """
    if not path:
        return None
    if not path.startswith("/") or path.startswith("//") or "://" in path:
        return None
    return path
