"""
Release Client
Handles GitCode release manifest lookups for update checking.
"""

from __future__ import annotations

import base64
import json
import os
from typing import Optional
from urllib.parse import unquote, urlparse

import requests

GITCODE_OWNER = "Re2347"
GITCODE_RELEASE_REPO = "guoneibanrosedl"
GITCODE_RELEASE_BRANCH = "main"

DEFAULT_UPDATE_MANIFEST_URL = (
    f"https://gitcode.com/api/v5/repos/{GITCODE_OWNER}/{GITCODE_RELEASE_REPO}"
    f"/raw/latest.json?ref={GITCODE_RELEASE_BRANCH}"
)
DEFAULT_GITCODE_RELEASE_API = (
    f"https://api.gitcode.com/api/v5/repos/{GITCODE_OWNER}/{GITCODE_RELEASE_REPO}"
    "/releases/latest"
)

UPDATE_MANIFEST_URL_ENV = "ROSE_UPDATE_MANIFEST_URL"
UPDATE_RELEASE_API_URL_ENV = "ROSE_UPDATE_RELEASE_API_URL"


class GitHubClient:
    """Compatibility wrapper for update release lookups."""
    
    def __init__(
        self,
        timeout: int = 20,
        manifest_url: Optional[str] = None,
        release_api_url: Optional[str] = None,
    ):
        self.timeout = timeout
        self.manifest_url = self._configured_url(
            manifest_url,
            UPDATE_MANIFEST_URL_ENV,
            DEFAULT_UPDATE_MANIFEST_URL,
        )
        self.release_api_url = self._configured_url(
            release_api_url,
            UPDATE_RELEASE_API_URL_ENV,
            DEFAULT_GITCODE_RELEASE_API,
        )
    
    def get_latest_release(self) -> Optional[dict]:
        """Get the latest release information from GitCode.
        
        Returns:
            Release data dictionary or None if failed
        """
        for loader in (self._get_manifest_release, self._get_api_release):
            try:
                release = loader()
            except Exception:  # noqa: BLE001
                release = None
            if release:
                return release
        return None
    
    def get_release_version(self, release: dict) -> str:
        """Extract version string from release data"""
        return release.get("tag_name") or release.get("version") or release.get("name") or ""
    
    def get_zip_asset(self, release: dict) -> Optional[dict]:
        """Get the ZIP asset from release data"""
        assets = release.get("assets", [])
        zip_assets = [
            asset for asset in assets if asset.get("name", "").lower().endswith(".zip")
        ]
        if not zip_assets:
            return None

        def asset_score(asset: dict) -> int:
            name = asset.get("name", "").lower()
            score = 0
            if asset.get("type") != "source":
                score += 10
            if "rose" in name:
                score += 5
            if "cn" in name:
                score += 3
            return score

        return max(zip_assets, key=asset_score)
    
    def get_hash_asset(self, release: dict) -> Optional[dict]:
        """Get the hash file asset from release data"""
        assets = release.get("assets", [])
        return next((a for a in assets if a.get("name", "").lower() == "hashes.game.txt"), None)

    @staticmethod
    def _configured_url(value: Optional[str], env_name: str, default: str) -> str:
        if value is not None:
            return value
        return os.environ.get(env_name) or default

    def _get_manifest_release(self) -> Optional[dict]:
        if not self.manifest_url:
            return None
        response = requests.get(self.manifest_url, timeout=self.timeout)
        response.raise_for_status()
        manifest = self._decode_manifest_payload(response.json())
        if not manifest:
            return None
        return self._manifest_to_release(manifest)

    def _get_api_release(self) -> Optional[dict]:
        if not self.release_api_url:
            return None
        response = requests.get(self.release_api_url, timeout=self.timeout)
        response.raise_for_status()
        release = response.json()
        return release if isinstance(release, dict) else None

    @staticmethod
    def _decode_manifest_payload(payload: object) -> Optional[dict]:
        if not isinstance(payload, dict):
            return None
        if payload.get("encoding") == "base64" and payload.get("content"):
            raw = base64.b64decode(str(payload["content"]))
            decoded = json.loads(raw.decode("utf-8"))
            return decoded if isinstance(decoded, dict) else None
        return payload

    @classmethod
    def _manifest_to_release(cls, manifest: dict) -> Optional[dict]:
        version = cls._string_value(manifest.get("version") or manifest.get("tag_name"))
        download_url = cls._string_value(
            manifest.get("download_url") or manifest.get("browser_download_url")
        )
        if not version or not download_url:
            return None

        asset_name = (
            cls._string_value(manifest.get("asset_name") or manifest.get("file_name"))
            or cls._filename_from_download_url(download_url)
            or f"Rose-CN-{version}.zip"
        )
        size = cls._integer_value(manifest.get("size"))
        sha256 = cls._string_value(manifest.get("sha256") or manifest.get("checksum"))

        asset = {
            "name": asset_name,
            "browser_download_url": download_url,
            "type": "package",
        }
        if size is not None:
            asset["size"] = size
        if sha256:
            asset["sha256"] = sha256.strip().lower()

        assets = [asset]
        hash_url = cls._string_value(manifest.get("hash_url") or manifest.get("hashes_url"))
        if hash_url:
            assets.append(
                {
                    "name": "hashes.game.txt",
                    "browser_download_url": hash_url,
                    "type": "hash",
                }
            )

        release = {
            "tag_name": version,
            "name": cls._string_value(manifest.get("title") or manifest.get("name")) or version,
            "body": manifest.get("body") or manifest.get("notes") or "",
            "assets": assets,
            "manifest": manifest,
        }
        if sha256:
            release["sha256"] = sha256.strip().lower()
        return release

    @staticmethod
    def _filename_from_download_url(download_url: str) -> str:
        parts = [part for part in urlparse(download_url).path.split("/") if part]
        if not parts:
            return ""
        candidate = parts[-2] if parts[-1].lower() == "download" and len(parts) >= 2 else parts[-1]
        return unquote(candidate)

    @staticmethod
    def _string_value(value: object) -> str:
        return value.strip() if isinstance(value, str) else ""

    @staticmethod
    def _integer_value(value: object) -> Optional[int]:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
        return None
