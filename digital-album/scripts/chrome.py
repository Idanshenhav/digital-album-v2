"""Find a Chrome/Chromium the scripts can run headless (titles, map labels, spreads, cover title).

Works on a Mac (Google Chrome app) and in Linux sandboxes such as Cowork (chromium, google-chrome,
or the Chromium that `python3 -m playwright install chromium` downloads). Set CHROME=/path to override.
"""
import glob
import os
import shutil

_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
]


def find() -> str:
    """Path of a usable browser, or raise with a clear fix."""
    env = os.environ.get("CHROME")
    if env:
        return env
    for c in _CANDIDATES:
        p = c if os.path.isabs(c) else shutil.which(c)
        if p and os.path.exists(p):
            return p
    for pat in ("~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome",
                "~/Library/Caches/ms-playwright/chromium-*/chrome-mac*/Chromium.app/Contents/MacOS/Chromium"):
        hits = sorted(glob.glob(os.path.expanduser(pat)))
        if hits:
            return hits[-1]
    raise SystemExit("No Chrome/Chromium found. Fix: pip install playwright && python3 -m playwright install chromium "
                     "(or set CHROME=/path/to/chrome).")


try:
    CHROME = find()
except SystemExit as e:  # only scripts that render need it; they fail with this hint
    CHROME = "chrome-not-found:see-references/cowork-setup.md"
    print(e)
_HAS_TIMEOUT = shutil.which("timeout") is not None


def T(seconds: int) -> list[str]:
    """`timeout N` prefix when the command exists (Linux, Macs with coreutils); empty otherwise."""
    return ["timeout", str(seconds)] if _HAS_TIMEOUT else []


def TS(seconds: int) -> str:
    """Same as T() for shell strings."""
    return f"timeout {seconds} " if _HAS_TIMEOUT else ""
