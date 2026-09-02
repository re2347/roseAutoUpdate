import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import subprocess

from utils.download.repo_downloader import RepoDownloader


class GitCodeRepositoryDownloaderTests(unittest.TestCase):
    def test_uses_gitcode_as_the_default_skin_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            downloader = RepoDownloader(target_dir=Path(temp_dir))

        self.assertEqual(
            downloader.repo_url,
            "https://gitcode.com/Re2347/cloneSkin.git",
        )

    def test_reads_the_main_revision_from_a_git_remote(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            origin = temp_path / "origin.git"
            checkout = temp_path / "checkout"
            self._run_git("init", "--bare", str(origin))
            self._run_git("init", "--initial-branch=main", str(checkout))
            self._run_git("-C", str(checkout), "config", "user.name", "Rose test")
            self._run_git("-C", str(checkout), "config", "user.email", "rose@example.com")
            (checkout / "README.md").write_text("skin repository", encoding="utf-8")
            self._run_git("-C", str(checkout), "add", "README.md")
            self._run_git("-C", str(checkout), "commit", "-m", "initial")
            self._run_git("-C", str(checkout), "remote", "add", "origin", str(origin))
            self._run_git("-C", str(checkout), "push", "origin", "main")

            downloader = RepoDownloader(target_dir=temp_path / "skins", repo_url=str(origin))

            self.assertEqual(
                downloader.fetch_remote_sha(),
                subprocess.run(
                    ["git", "-C", str(checkout), "rev-parse", "HEAD"],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip(),
            )

    def test_syncs_gitcode_checkout_into_the_existing_rose_layout(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_root = temp_path / "cloneSkin-main"
            target_dir = temp_path / "rose-skins"
            user_data_dir = temp_path / "rose-data"

            skin_file = source_root / "skins" / "1" / "1001" / "1001.fantome"
            resource_file = source_root / "resources" / "skins.json"
            ignored_classic_file = source_root / "classic" / "1" / "1001" / "1001.fantome"
            skin_file.parent.mkdir(parents=True)
            resource_file.parent.mkdir(parents=True)
            ignored_classic_file.parent.mkdir(parents=True)
            skin_file.write_bytes(b"skin")
            resource_file.write_text("{}", encoding="utf-8")
            ignored_classic_file.write_bytes(b"classic")

            downloader = RepoDownloader(target_dir=target_dir)
            with patch("utils.core.paths.get_user_data_dir", return_value=user_data_dir):
                self.assertTrue(downloader.sync_checkout(source_root))

            self.assertEqual(
                (target_dir / "1" / "1001" / "1001.fantome").read_bytes(),
                b"skin",
            )
            self.assertEqual(
                (user_data_dir / "resources" / "skins.json").read_text(encoding="utf-8"),
                "{}",
            )
            self.assertFalse((target_dir / "classic").exists())

    @staticmethod
    def _run_git(*args):
        subprocess.run(["git", *args], check=True, capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()
