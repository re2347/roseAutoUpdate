import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.package_cn_release import build_manifest, create_portable_zip


class CNReleasePackagingTests(unittest.TestCase):
    def test_creates_update_zip_with_rose_top_level_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dist_dir = root / "dist" / "Rose"
            dist_dir.mkdir(parents=True)
            (dist_dir / "Rose.exe").write_bytes(b"exe")
            (dist_dir / "_internal").mkdir()
            (dist_dir / "_internal" / "config.dat").write_bytes(b"data")

            zip_path = create_portable_zip(
                dist_dir=dist_dir,
                output_dir=root / "release",
                version="1.2.14",
            )

            with zipfile.ZipFile(zip_path) as archive:
                names = set(archive.namelist())

        self.assertIn("Rose/Rose.exe", names)
        self.assertIn("Rose/_internal/config.dat", names)

    def test_builds_manifest_for_gitcode_release_attachment(self):
        manifest = build_manifest(
            version="1.2.14",
            asset_name="Rose-CN-1.2.14.zip",
            size=123,
            sha256="b" * 64,
            owner="Re2347",
            repo="guoneibanrosedl",
            tag="1.2.14",
        )

        self.assertEqual(manifest["version"], "1.2.14")
        self.assertEqual(manifest["asset_name"], "Rose-CN-1.2.14.zip")
        self.assertEqual(manifest["size"], 123)
        self.assertEqual(manifest["sha256"], "b" * 64)
        self.assertEqual(
            manifest["download_url"],
            "https://api.gitcode.com/api/v5/repos/Re2347/guoneibanrosedl/"
            "releases/1.2.14/attach_files/Rose-CN-1.2.14.zip/download",
        )


if __name__ == "__main__":
    unittest.main()
