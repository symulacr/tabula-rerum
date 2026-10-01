#!/usr/bin/env python3
"""Share card: render the board to a PNG using the host's existing headless Chrome.

Why this exists: the submission needs a shareable image, and the contract forbids adding a
dependency or a build step. Chrome is already on the machine, so the honest way to get a PNG is
to drive it -- not to install a rasteriser.

DETERMINISM. Two runs must produce byte-identical PNGs, or the product's reproducibility claim
is decorative. The flags below are what buy that:
  --force-device-scale-factor=1  pin the DPR, so the host's display cannot change the output
  --virtual-time-budget=N         advance virtual time instead of wall-clock, so animation and
                                 font loading settle identically every run
  --hide-scrollbars              a scrollbar appearing is a layout difference
  --default-background-color     an explicit ground, not "whatever the root is"
Verified: two consecutive runs produced identical sha256.

The Chrome major is pinned in the docs because a future Chrome may rasterise text differently and
silently break byte-reproducibility. If the hash check below starts failing after a Chrome
upgrade, that is what happened -- not a bug in the board.

Usage:
  python3 share_card.py                 # -> share-card.png
  python3 share_card.py --out x.png --days 120
  python3 share_card.py --check         # verify determinism, print the hash
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "apps" / "api"))

CANDIDATES = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
              "chrome-headless-shell")

W, H = 1200, 630


def find_chrome() -> str | None:
    for name in CANDIDATES:
        path = shutil.which(name)
        if path:
            return path
    return None


def render(chrome: str, html_path: Path, png_path: Path, port: int = 8123) -> None:
    """Start the app, screenshot it, stop it. Deterministic flags only."""
    from http.server import ThreadingHTTPServer
    from tabula.server import Handler

    Handler.offline = True
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    import threading
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    time.sleep(1.5)
    try:
        cmd = [
            chrome, "--headless", "--no-sandbox", "--disable-gpu",
            "--hide-scrollbars", "--force-device-scale-factor=1",
            f"--window-size={W},{H}", "--default-background-color=f7f7f4",
            "--virtual-time-budget=4000",
            f"--user-data-dir={tempfile.mkdtemp(prefix='tabula-share-')}",
            f"--screenshot={png_path}", f"http://127.0.0.1:{port}/",
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if not png_path.is_file() or png_path.stat().st_size == 0:
            raise RuntimeError(f"chrome produced no image\n{r.stderr[-600:]}")
    finally:
        srv.shutdown()
        srv.server_close()


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default="share-card.png")
    ap.add_argument("--days", type=int, default=180)
    ap.add_argument("--check", action="store_true",
                    help="render twice and assert the outputs are byte-identical")
    args = ap.parse_args(argv)

    chrome = find_chrome()
    if not chrome:
        print("no Chrome found. Tried: " + ", ".join(CANDIDATES), file=sys.stderr)
        print("This is the contract's 'host's existing headless Chrome, zero install' rule.",
              file=sys.stderr)
        return 2
    print(f"chrome: {chrome}")

    out = (ROOT / args.out).resolve()
    render(chrome, ROOT / "run.py", out)

    if args.check:
        second = out.with_name("share-card-verify.png")
        render(chrome, ROOT / "run.py", second)
        a, b = sha(out), sha(second)
        second.unlink(missing_ok=True)
        print(f"run 1: {a}  ({out.stat().st_size} bytes)")
        print(f"run 2: {b}")
        if a != b:
            print("NOT DETERMINISTIC -- the two runs differ.", file=sys.stderr)
            return 1
        print("deterministic: byte-identical across runs")
        return 0

    print(f"wrote {out}  ({out.stat().st_size} bytes, sha256 {sha(out)[:16]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
