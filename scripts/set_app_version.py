#!/usr/bin/env python3
"""Set config.APP_VERSION for a release build."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION_PATTERN = re.compile(r"^\d+(?:\.\d+){1,3}$")
APP_VERSION_PATTERN = re.compile(
    r'(?m)^(APP_VERSION\s*=\s*)(["\'])([^"\']+)(["\'])'
)


def validate_version(version: str) -> str:
    if not VERSION_PATTERN.fullmatch(version):
        raise ValueError(
            "Version must use numeric dot-separated parts, for example 1.2.14 or 1.2.14.1"
        )
    return version


def replace_app_version_text(text: str, version: str) -> str:
    validate_version(version)
    updated, count = APP_VERSION_PATTERN.subn(
        lambda match: f"{match.group(1)}{match.group(2)}{version}{match.group(4)}",
        text,
        count=1,
    )
    if count != 1:
        raise ValueError("Could not find exactly one APP_VERSION assignment")
    return updated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version")
    parser.add_argument("--config", type=Path, default=ROOT / "config.py")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    text = args.config.read_text(encoding="utf-8")
    args.config.write_text(replace_app_version_text(text, args.version), encoding="utf-8")
    print(f"Set APP_VERSION to {args.version} in {args.config}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
