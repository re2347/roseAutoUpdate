import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from launcher.update.update_sequence import UpdateSequence


class FakeReleaseClient:
    def __init__(self):
        self.asset = {
            "name": "Rose-CN-2.0.0.zip",
            "browser_download_url": "https://gitcode.example/Rose-CN-2.0.0.zip",
            "size": 12,
            "sha256": "0" * 64,
        }
        self.release = {
            "tag_name": "2.0.0",
            "assets": [self.asset],
        }

    def get_latest_release(self):
        return self.release

    def get_release_version(self, release):
        return release["tag_name"]

    def get_zip_asset(self, release):
        return release["assets"][0]

    def get_hash_asset(self, release):
        return None


class WritingDownloader:
    def download_update(
        self,
        download_url,
        zip_path,
        status_callback,
        bytes_callback=None,
        total_size=None,
    ):
        zip_path.write_bytes(b"not this package")
        return True

    def verify_sha256(self, path, expected_sha256):
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        return actual == expected_sha256.lower()


class InstallerThatMustNotRun:
    def __init__(self):
        self.extract_called = False

    def extract_update(self, *args, **kwargs):
        self.extract_called = True
        raise AssertionError("bad update package should not be extracted")


class UpdateSequenceChecksumTests(unittest.TestCase):
    def test_stops_before_extracting_when_update_package_checksum_mismatches(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.ini"
            statuses = []
            installer = InstallerThatMustNotRun()
            sequence = UpdateSequence()
            sequence.github_client = FakeReleaseClient()
            sequence.downloader = WritingDownloader()
            sequence.installer = installer

            with patch(
                "launcher.update.update_sequence.get_config_file_path",
                return_value=config_path,
            ), patch("launcher.update.update_sequence.APP_VERSION", "1.0.0"):
                result = sequence.perform_update(
                    status_callback=statuses.append,
                    progress_callback=lambda value: None,
                )

        self.assertFalse(result)
        self.assertFalse(installer.extract_called)
        self.assertTrue(
            any("checksum" in status.lower() for status in statuses),
            statuses,
        )


if __name__ == "__main__":
    unittest.main()
