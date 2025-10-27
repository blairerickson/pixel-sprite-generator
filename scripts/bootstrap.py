"""Cross-platform setup utilities for Pixel Sprite Generator.

This script prepares the backend virtual environment, primes the
stable-diffusion-webui checkout, downloads required model assets,
and creates common runtime directories.  It is designed to be invoked
both directly (``python scripts/bootstrap.py setup``) and indirectly via
the platform specific wrappers that ship with the project.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
SD_DIR = ROOT_DIR / "stable-diffusion-webui"

DEFAULT_MANIFEST = ROOT_DIR / "sd-assets.manifest.json"


class BootstrapError(RuntimeError):
    """Fatal error triggered during setup."""


def log(msg: str) -> None:
    print(f"[bootstrap] {msg}")


def run(cmd: List[str], cwd: Optional[Path] = None, env: Optional[dict] = None) -> None:
    pretty = " ".join(cmd)
    log(f"$ {pretty}")
    try:
        subprocess.run(cmd, cwd=cwd, env=env, check=True)
    except subprocess.CalledProcessError as exc:
        raise BootstrapError(f"Command failed with exit code {exc.returncode}: {pretty}") from exc


def ensure_directories() -> None:
    for rel in ("output", "temp", "cache"):
        path = ROOT_DIR / rel
        path.mkdir(parents=True, exist_ok=True)
        log(f"ensured directory {path.relative_to(ROOT_DIR)}")


def backend_python() -> Path:
    if sys.platform == "win32":
        return BACKEND_DIR / "venv" / "Scripts" / "python.exe"
    return BACKEND_DIR / "venv" / "bin" / "python"


def backend_pip() -> Path:
    if sys.platform == "win32":
        return BACKEND_DIR / "venv" / "Scripts" / "pip.exe"
    return BACKEND_DIR / "venv" / "bin" / "pip"


def create_backend_venv(python: Optional[str] = None) -> None:
    target = BACKEND_DIR / "venv"
    if target.exists():
        log("backend virtual environment already present")
        return

    python_cmd = python or sys.executable
    log(f"creating backend virtual environment with {python_cmd}")
    run([python_cmd, "-m", "venv", str(target)])


def install_backend_requirements() -> None:
    pip = backend_pip()
    if not pip.exists():
        raise BootstrapError("backend virtual environment missing – run create_backend_venv() first")

    requirements = BACKEND_DIR / "requirements.txt"
    log("upgrading pip inside backend venv")
    run([str(pip), "install", "--upgrade", "pip"])
    log("installing backend requirements")
    run([str(pip), "install", "-r", str(requirements)])


def bootstrap_sd_environment(python: Optional[str] = None, force: bool = False) -> None:
    venv_dir = SD_DIR / "venv"
    if venv_dir.exists() and not force:
        log("stable-diffusion-webui venv already exists; skipping bootstrap")
        return

    if not SD_DIR.exists():
        raise BootstrapError("stable-diffusion-webui folder missing – please check repository layout")

    log("bootstrapping stable-diffusion-webui environment (this may take several minutes)")

    env = os.environ.copy()
    extra_args = "--api --listen --port 7860 --exit"
    env.setdefault("COMMANDLINE_ARGS", extra_args)
    cmd: List[str]
    cwd = SD_DIR

    if sys.platform == "win32":
        cmd = ["cmd.exe", "/c", "call", "webui.bat"]
        env.setdefault("PYTHON", python or "")
    else:
        script = SD_DIR / "webui.sh"
        cmd = ["bash", str(script)]
        if python:
            env.setdefault("PYTHON", python)

    try:
        run(cmd, cwd=cwd, env=env)
    except BootstrapError as exc:
        raise BootstrapError(
            "Failed to prime stable-diffusion-webui. Review the output above "
            "and resolve any missing GPU drivers or Python dependencies."
        ) from exc


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class Asset:
    name: str
    target: Path
    sha256: str
    size: Optional[int]
    urls: List[str]

    @classmethod
    def from_dict(cls, data: dict) -> "Asset":
        urls = [str(u) for u in data.get("urls") or []]

        target = ROOT_DIR / data["target"]
        return cls(
            name=data.get("name", target.name),
            target=target,
            sha256=data.get("sha256", "").lower(),
            size=data.get("size"),
            urls=urls,
        )


def load_manifest(path: Path) -> List[Asset]:
    if not path.exists():
        raise BootstrapError(
            f"Asset manifest '{path}' not found. Ensure the manifest exists or specify --manifest."
        )

    with path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)

    items = raw.get("assets") if isinstance(raw, dict) else raw
    if not isinstance(items, Iterable):
        raise BootstrapError("Asset manifest must contain an 'assets' list")

    assets = [Asset.from_dict(entry) for entry in items]
    log(f"loaded {len(assets)} assets from manifest {path}")
    return assets


def download_asset(asset: Asset, timeout: int = 60) -> None:
    asset.target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = asset.target.with_suffix(asset.target.suffix + ".part")

    for url in asset.urls:
        url = os.path.expandvars(url)
        log(f"downloading {asset.name} from {url}")
        try:
            start = time.time()
            with urlopen(Request(url, headers={"User-Agent": "PixelSpriteBootstrap/1.0"}), timeout=timeout) as resp, (
                tmp_path.open("wb")
            ) as out:
                total = int(resp.headers.get("Content-Length", "0"))
                downloaded = 0
                while True:
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        percent = downloaded / total * 100
                        elapsed = time.time() - start
                        log(f"  {percent:5.1f}% ({downloaded/1_048_576:.1f} MiB) in {elapsed:.1f}s",)
        except (HTTPError, URLError) as exc:
            log(f"  failed: {exc}. Trying next mirror...")
            continue

        if asset.sha256:
            digest = sha256_file(tmp_path)
            if digest.lower() != asset.sha256:
                log(
                    f"  checksum mismatch for {asset.name} (expected {asset.sha256}, got {digest})."
                    " Trying next mirror..."
                )
                tmp_path.unlink(missing_ok=True)
                continue

        tmp_path.replace(asset.target)
        log(f"  saved to {asset.target.relative_to(ROOT_DIR)}")
        return

    if not asset.urls:
        raise BootstrapError(
            f"No download URLs defined for {asset.name}. Update sd-assets.manifest.json with a mirror or place the file manually at {asset.target}."
        )

    raise BootstrapError(f"Unable to download {asset.name}; all mirrors failed or checksums mismatched")


def sync_assets(manifest: Path, only_missing: bool = True) -> None:
    assets = load_manifest(manifest)
    for asset in assets:
        if asset.target.exists():
            if asset.sha256:
                digest = sha256_file(asset.target)
                if digest.lower() == asset.sha256:
                    log(f"asset '{asset.name}' already present and verified")
                    if only_missing:
                        continue
                else:
                    log(f"asset '{asset.name}' present but checksum mismatch; redownloading")
            elif only_missing:
                log(f"asset '{asset.name}' already present (no checksum provided)")
                continue

        download_asset(asset)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap Pixel Sprite Generator components")
    sub = parser.add_subparsers(dest="command", required=True)

    setup = sub.add_parser("setup", help="Prepare backend, Stable Diffusion, and assets")
    setup.add_argument("--python", help="Python executable to use for venv creation")
    setup.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Path to asset manifest JSON")
    setup.add_argument("--skip-assets", action="store_true", help="Skip asset download step")
    setup.add_argument("--force-sd-bootstrap", action="store_true", help="Re-run stable diffusion bootstrap even if venv exists")
    setup.add_argument("--skip-sd-bootstrap", action="store_true", help="Do not touch stable diffusion environment")

    download = sub.add_parser("download-assets", help="Download or refresh Stable Diffusion assets")
    download.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Path to asset manifest JSON")
    download.add_argument("--refresh", action="store_true", help="Re-download even if files exist")

    return parser.parse_args()


def cmd_setup(args: argparse.Namespace) -> None:
    ensure_directories()
    create_backend_venv(args.python)
    install_backend_requirements()

    if not args.skip_sd_bootstrap:
        bootstrap_sd_environment(args.python, force=args.force_sd_bootstrap)
    else:
        log("skipping stable diffusion bootstrap as requested")

    if not args.skip_assets:
        sync_assets(Path(args.manifest), only_missing=True)
    else:
        log("skipping asset download as requested")

    log("setup complete")


def cmd_download(args: argparse.Namespace) -> None:
    sync_assets(Path(args.manifest), only_missing=not args.refresh)


def main() -> None:
    try:
        args = parse_args()
        if args.command == "setup":
            cmd_setup(args)
        elif args.command == "download-assets":
            cmd_download(args)
        else:
            raise BootstrapError(f"unknown command: {args.command}")
    except BootstrapError as exc:
        print(textwrap.fill(str(exc), width=100), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()


