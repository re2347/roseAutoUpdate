import builtins
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.publish_gitcode_release import (
    DEFAULT_UPLOAD_TIMEOUT,
    GitCodePublisher,
    PublishDecision,
    choose_publish_decision,
    validate_zip,
)


class PublishGitCodeReleaseTests(unittest.TestCase):
    def test_skips_when_current_manifest_matches_version_and_hash(self):
        decision = choose_publish_decision(
            existing_manifest={"version": "1.2.14", "sha256": "a" * 64},
            new_manifest={"version": "1.2.14", "sha256": "A" * 64},
        )

        self.assertEqual(decision, PublishDecision.SKIP)

    def test_requires_version_bump_when_same_version_has_different_hash(self):
        decision = choose_publish_decision(
            existing_manifest={"version": "1.2.14", "sha256": "a" * 64},
            new_manifest={"version": "1.2.14", "sha256": "b" * 64},
        )

        self.assertEqual(decision, PublishDecision.VERSION_CONFLICT)

    def test_publishes_when_version_is_new(self):
        decision = choose_publish_decision(
            existing_manifest={"version": "1.2.14", "sha256": "a" * 64},
            new_manifest={"version": "1.2.15", "sha256": "b" * 64},
        )

        self.assertEqual(decision, PublishDecision.PUBLISH)

    def test_validate_zip_falls_back_when_run_as_script(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            zip_path = root / "Rose-CN-1.2.14.zip"
            zip_path.write_bytes(b"rose")
            manifest = {"sha256": hashlib.sha256(b"rose").hexdigest()}

            scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
            original_sys_path = sys.path[:]
            original_modules = {
                name: sys.modules.get(name)
                for name in ("scripts.package_cn_release", "package_cn_release")
            }
            original_import = builtins.__import__

            def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
                if name == "scripts.package_cn_release" or (
                    name == "scripts" and fromlist and "package_cn_release" in fromlist
                ):
                    raise ModuleNotFoundError(
                        "No module named 'scripts.package_cn_release'",
                        name="scripts.package_cn_release",
                    )
                return original_import(name, globals, locals, fromlist, level)

            try:
                sys.path.insert(0, str(scripts_dir))
                sys.modules.pop("scripts.package_cn_release", None)
                sys.modules.pop("package_cn_release", None)

                with mock.patch("builtins.__import__", side_effect=fake_import):
                    validate_zip(zip_path, manifest)
            finally:
                sys.path[:] = original_sys_path
                for name, module in original_modules.items():
                    if module is None:
                        sys.modules.pop(name, None)
                    else:
                        sys.modules[name] = module

    def test_upload_asset_uses_a_longer_upload_timeout(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = Path(temp_dir) / "Rose-CN-1.2.14.zip"
            zip_path.write_bytes(b"rose")
            publisher = GitCodePublisher(
                owner="Re2347",
                repo="guoneibanrosedl",
                token="token",
            )

            upload_response = mock.Mock(
                status_code=200,
                text="",
                json=mock.Mock(
                    return_value={
                        "url": "https://upload.example.com/release.bin",
                        "headers": {"Content-Type": "application/zip"},
                    }
                ),
            )
            put_response = mock.Mock(status_code=201, text="")
            with mock.patch(
                "scripts.publish_gitcode_release.requests.request",
                side_effect=[upload_response, put_response],
            ) as request:
                publisher.upload_asset(
                    zip_path,
                    {"version": "1.2.14", "asset_name": zip_path.name},
                )

            self.assertEqual(
                request.call_args_list[1].kwargs["timeout"], DEFAULT_UPLOAD_TIMEOUT
            )

    def test_upload_asset_uses_gitcode_upload_url_flow(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = Path(temp_dir) / "Rose-CN-1.2.14.zip"
            zip_path.write_bytes(b"rose")
            publisher = GitCodePublisher(
                owner="Re2347",
                repo="guoneibanrosedl",
                token="token",
            )

            upload_response = mock.Mock(
                status_code=200,
                text="",
                json=mock.Mock(
                    return_value={
                        "url": "https://upload.example.com/release.bin",
                        "headers": {
                            "x-obs-meta-project-id": "123",
                            "x-obs-acl": "public-read",
                            "x-obs-callback": "callback",
                            "Content-Type": "application/zip",
                        },
                    }
                ),
            )
            put_response = mock.Mock(status_code=201, text="")

            with mock.patch(
                "scripts.publish_gitcode_release.requests.request",
                side_effect=[upload_response, put_response],
            ) as request:
                publisher.upload_asset(
                    zip_path,
                    {"version": "1.2.14", "asset_name": zip_path.name},
                )

            self.assertEqual(request.call_args_list[0].args[0], "GET")
            self.assertIn("upload_url", request.call_args_list[0].args[1])
            self.assertEqual(
                request.call_args_list[0].kwargs["params"]["file_name"], zip_path.name
            )
            self.assertEqual(request.call_args_list[1].args[0], "PUT")
            self.assertEqual(
                request.call_args_list[1].args[1], "https://upload.example.com/release.bin"
            )
            self.assertEqual(
                request.call_args_list[1].kwargs["headers"]["x-obs-meta-project-id"], "123"
            )
            self.assertEqual(
                request.call_args_list[1].kwargs["timeout"], DEFAULT_UPLOAD_TIMEOUT
            )


if __name__ == "__main__":
    unittest.main()
