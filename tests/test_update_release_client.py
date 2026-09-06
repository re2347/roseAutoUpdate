import base64
import json
import unittest
from unittest.mock import patch

from launcher.update.github_client import GitHubClient


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class GitCodeManifestReleaseClientTests(unittest.TestCase):
    def test_reads_gitcode_manifest_as_release(self):
        manifest = {
            "version": "1.2.14.1",
            "title": "Rose CN 1.2.14.1",
            "download_url": "https://api.gitcode.com/download/Rose-CN-1.2.14.1.zip",
            "asset_name": "Rose-CN-1.2.14.1.zip",
            "size": 12345,
            "sha256": "a" * 64,
        }

        with patch(
            "launcher.update.github_client.requests.get",
            return_value=FakeResponse(manifest),
        ) as get:
            client = GitHubClient(
                timeout=7,
                manifest_url="https://gitcode.example/latest.json",
                release_api_url="https://gitcode.example/releases/latest",
            )
            release = client.get_latest_release()

        get.assert_called_once_with("https://gitcode.example/latest.json", timeout=7)
        self.assertEqual(release["tag_name"], "1.2.14.1")
        self.assertEqual(release["name"], "Rose CN 1.2.14.1")

        asset = client.get_zip_asset(release)
        self.assertEqual(asset["name"], "Rose-CN-1.2.14.1.zip")
        self.assertEqual(asset["browser_download_url"], manifest["download_url"])
        self.assertEqual(asset["size"], 12345)
        self.assertEqual(asset["sha256"], "a" * 64)

    def test_decodes_gitcode_contents_api_manifest(self):
        manifest = {
            "version": "1.2.15",
            "download_url": "https://api.gitcode.com/download/Rose-CN-1.2.15.zip",
        }
        payload = {
            "encoding": "base64",
            "content": base64.b64encode(json.dumps(manifest).encode("utf-8")).decode("ascii"),
        }

        with patch(
            "launcher.update.github_client.requests.get",
            return_value=FakeResponse(payload),
        ):
            client = GitHubClient(
                manifest_url="https://gitcode.example/contents/latest.json",
                release_api_url="https://gitcode.example/releases/latest",
            )
            release = client.get_latest_release()

        self.assertEqual(release["tag_name"], "1.2.15")
        self.assertEqual(
            client.get_zip_asset(release)["browser_download_url"],
            "https://api.gitcode.com/download/Rose-CN-1.2.15.zip",
        )

    def test_prefers_rose_package_zip_over_gitcode_source_zip(self):
        release = {
            "tag_name": "1.2.15",
            "assets": [
                {
                    "name": "v1.2.15.zip",
                    "type": "source",
                    "browser_download_url": "https://raw.gitcode.com/source.zip",
                },
                {
                    "name": "Rose-CN-1.2.15.zip",
                    "type": "package",
                    "browser_download_url": "https://api.gitcode.com/package.zip",
                },
            ],
        }

        self.assertEqual(
            GitHubClient().get_zip_asset(release)["browser_download_url"],
            "https://api.gitcode.com/package.zip",
        )


if __name__ == "__main__":
    unittest.main()
