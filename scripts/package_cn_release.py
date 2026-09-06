#!/usr/bin/env python3
"""Package a Rose CN portable release and write its GitCode update manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OWNER = "Re2347"
DEFAULT_REPO = "guoneibanrosedl"


def calculate_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_portable_zip(dist_dir: Path, output_dir: Path, version: str) -> Path:
    """Create a ZIP whose top-level directory is the dist folder name."""
    dist_dir = dist_dir.resolve()
    if not dist_dir.exists() or not dist_dir.is_dir():
        raise FileNotFoundError(f"dist directory not found: {dist_dir}")
    if not (dist_dir / "Rose.exe").exists():
        raise FileNotFoundError(f"Rose.exe not found in {dist_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f"Rose-CN-{version}.zip"
    if zip_path.exists():
        zip_path.unlink()

    root_name = dist_dir.name
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source in sorted(path for path in dist_dir.rglob("*") if path.is_file()):
            archive.write(source, Path(root_name) / source.relative_to(dist_dir))
    return zip_path


def gitcode_release_asset_url(owner: str, repo: str, tag: str, asset_name: str) -> str:
    encoded_tag = quote(tag, safe="")
    encoded_asset = quote(asset_name, safe="")
    return (
        f"https://api.gitcode.com/api/v5/repos/{owner}/{repo}/releases/"
        f"{encoded_tag}/attach_files/{encoded_asset}/download"
    )


def build_manifest(
    *,
    version: str,
    asset_name: str,
    size: int,
    sha256: str,
    owner: str,
    repo: str,
    tag: str,
) -> dict:
    return {
        "version": version,
        "title": f"Rose CN {version}",
        "download_url": gitcode_release_asset_url(owner, repo, tag, asset_name),
        "asset_name": asset_name,
        "size": size,
        "sha256": sha256.lower(),
        "mandatory": False,
        "notes": [
            "Rose CN build with China server LCU compatibility.",
            "Skin downloads use the GitCode cloneSkin mirror.",
            "Software updates use the GitCode CN release channel.",
        ],
    }


def write_manifest(path: Path, manifest: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def read_default_version() -> str:
    sys.path.insert(0, str(ROOT))
    from config import APP_VERSION  # pylint: disable=import-outside-toplevel

    return APP_VERSION


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default=None, help="Release version; defaults to config.APP_VERSION.")
    parser.add_argument("--dist-dir", type=Path, default=ROOT / "dist" / "Rose")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "release")
    parser.add_argument("--owner", default=DEFAULT_OWNER)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--tag", default=None, help="GitCode release tag; defaults to --version.")
    parser.add_argument("--manifest-name", default="latest.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    version = args.version or read_default_version()
    tag = args.tag or version

    zip_path = create_portable_zip(args.dist_dir, args.output_dir, version)
    sha256 = calculate_sha256(zip_path)
    manifest = build_manifest(
        version=version,
        asset_name=zip_path.name,
        size=zip_path.stat().st_size,
        sha256=sha256,
        owner=args.owner,
        repo=args.repo,
        tag=tag,
    )
    manifest_path = args.output_dir / args.manifest_name
    write_manifest(manifest_path, manifest)

    print(f"Release ZIP: {zip_path}")
    print(f"SHA-256: {sha256}")
    print(f"Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
