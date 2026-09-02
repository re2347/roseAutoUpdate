#!/usr/bin/env python3
"""Publish a Rose CN package and latest.json manifest to GitCode."""

from __future__ import annotations

import argparse
import base64
from enum import Enum
import json
import os
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import requests


DEFAULT_OWNER = "Re2347"
DEFAULT_REPO = "guoneibanrosedl"
DEFAULT_BRANCH = "main"
DEFAULT_API_BASE = "https://api.gitcode.com/api/v5"


class PublishDecision(Enum):
    PUBLISH = "publish"
    SKIP = "skip"
    VERSION_CONFLICT = "version-conflict"


def choose_publish_decision(
    existing_manifest: Optional[dict],
    new_manifest: dict,
) -> PublishDecision:
    if not existing_manifest:
        return PublishDecision.PUBLISH

    existing_version = str(existing_manifest.get("version") or "")
    new_version = str(new_manifest.get("version") or "")
    if existing_version != new_version:
        return PublishDecision.PUBLISH

    existing_sha = str(existing_manifest.get("sha256") or "").lower()
    new_sha = str(new_manifest.get("sha256") or "").lower()
    if existing_sha and existing_sha == new_sha:
        return PublishDecision.SKIP
    return PublishDecision.VERSION_CONFLICT


class GitCodePublisher:
    def __init__(
        self,
        *,
        owner: str,
        repo: str,
        token: str,
        branch: str = DEFAULT_BRANCH,
        api_base: str = DEFAULT_API_BASE,
        timeout: int = 60,
    ):
        self.owner = owner
        self.repo = repo
        self.token = token
        self.branch = branch
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout

    def fetch_current_manifest(self) -> Optional[dict]:
        response = requests.get(
            self._api_url("raw/latest.json"),
            params={"ref": self.branch, "access_token": self.token},
            timeout=self.timeout,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def ensure_release(self, manifest: dict) -> None:
        tag = self._manifest_tag(manifest)
        release = self._request(
            "GET",
            f"releases/tags/{quote(tag, safe='')}",
            ok_statuses={200, 400, 404},
        )
        if release.status_code == 200:
            return

        self._request(
            "POST",
            "releases",
            data={
                "tag_name": tag,
                "name": manifest.get("title") or f"Rose CN {manifest['version']}",
                "body": "\n".join(manifest.get("notes") or []),
                "prerelease": "false",
            },
            ok_statuses={200, 201},
        )

    def upload_asset(self, zip_path: Path, manifest: dict) -> None:
        tag = self._manifest_tag(manifest)
        asset_name = manifest.get("asset_name") or zip_path.name
        with open(zip_path, "rb") as fh:
            self._request(
                "POST",
                f"releases/{quote(tag, safe='')}/attach_files",
                data={},
                files={"file": (asset_name, fh, "application/zip")},
                ok_statuses={200, 201},
            )

    def publish_manifest_file(self, manifest: dict, path: str = "latest.json") -> None:
        encoded_path = "/".join(quote(part, safe="") for part in path.split("/"))
        current = self._request(
            "GET",
            f"contents/{encoded_path}",
            params={"ref": self.branch},
            ok_statuses={200, 400, 404},
        )
        sha = None
        if current.status_code == 200:
            current_json = current.json()
            sha = current_json.get("sha") if isinstance(current_json, dict) else None

        content = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
        data = {
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "message": f"chore: publish Rose CN {manifest['version']}",
            "branch": self.branch,
        }
        if sha:
            data["sha"] = sha

        self._request(
            "PUT" if sha else "POST",
            f"contents/{encoded_path}",
            data=data,
            ok_statuses={200, 201},
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
        files: Optional[dict] = None,
        ok_statuses: set[int],
    ) -> requests.Response:
        params = dict(params or {})
        data = dict(data or {})
        if method.upper() == "GET":
            params["access_token"] = self.token
        else:
            data["access_token"] = self.token

        response = requests.request(
            method,
            self._api_url(path),
            params=params or None,
            data=data or None,
            files=files,
            timeout=self.timeout,
        )
        if response.status_code not in ok_statuses:
            body = response.text[:500].replace(self.token, "***")
            raise RuntimeError(
                f"GitCode API {method} {path} failed with HTTP {response.status_code}: {body}"
            )
        return response

    def _api_url(self, path: str) -> str:
        return f"{self.api_base}/repos/{self.owner}/{self.repo}/{path.lstrip('/')}"

    @staticmethod
    def _manifest_tag(manifest: dict) -> str:
        return str(manifest.get("tag") or manifest["version"])


def load_manifest(path: Path) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not manifest.get("version") or not manifest.get("download_url"):
        raise ValueError(f"Invalid manifest: {path}")
    return manifest


def validate_zip(zip_path: Path, manifest: dict) -> None:
    if not zip_path.exists():
        raise FileNotFoundError(zip_path)
    expected_sha = str(manifest.get("sha256") or "").lower()
    if not expected_sha:
        raise ValueError("Manifest must include sha256 before publishing")

    from scripts.package_cn_release import calculate_sha256  # pylint: disable=import-outside-toplevel

    actual_sha = calculate_sha256(zip_path)
    if actual_sha != expected_sha:
        raise ValueError(
            f"Local ZIP SHA-256 does not match manifest: expected {expected_sha}, got {actual_sha}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("release/latest.json"))
    parser.add_argument("--zip", dest="zip_path", type=Path, required=True)
    parser.add_argument("--owner", default=DEFAULT_OWNER)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--branch", default=DEFAULT_BRANCH)
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--token", default=os.environ.get("GITCODE_TOKEN"))
    parser.add_argument("--skip-if-current", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.token:
        raise SystemExit("GITCODE_TOKEN is required.")

    manifest = load_manifest(args.manifest)
    validate_zip(args.zip_path, manifest)

    publisher = GitCodePublisher(
        owner=args.owner,
        repo=args.repo,
        token=args.token,
        branch=args.branch,
        api_base=args.api_base,
    )

    if args.skip_if_current:
        existing_manifest = publisher.fetch_current_manifest()
        decision = choose_publish_decision(existing_manifest, manifest)
        if decision == PublishDecision.SKIP:
            print("GitCode latest.json already points to this package. Nothing to publish.")
            return 0
        if decision == PublishDecision.VERSION_CONFLICT:
            raise SystemExit(
                "GitCode latest.json already uses this version with a different SHA-256. "
                "Bump APP_VERSION, for example from 1.2.14 to 1.2.14.1."
            )

    publisher.ensure_release(manifest)
    publisher.upload_asset(args.zip_path, manifest)
    publisher.publish_manifest_file(manifest)
    print(f"Published Rose CN {manifest['version']} to {args.owner}/{args.repo}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
