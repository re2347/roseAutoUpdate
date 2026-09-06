import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from injection.game.game_detector import GameDetector


class FakeConfigManager:
    def __init__(self):
        self.saved_paths = None

    def load_league_path(self):
        return None

    def load_client_path(self):
        return None

    def save_paths(self, league_path, client_path):
        self.saved_paths = (league_path, client_path)


class GameDetectorTests(unittest.TestCase):
    def test_detects_wegame_sibling_game_directory_from_client_ux(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            install_dir = Path(temp_dir) / "英雄联盟"
            client_dir = install_dir / "LeagueClient"
            game_dir = install_dir / "Game"
            client_dir.mkdir(parents=True)
            game_dir.mkdir()
            (client_dir / "LeagueClient.exe").touch()
            (client_dir / "LeagueClientUx.exe").touch()
            (game_dir / "League of Legends.exe").touch()

            config = FakeConfigManager()
            detector = GameDetector(config)
            process = type(
                "FakeProcess",
                (),
                {
                    "info": {
                        "name": "LeagueClientUx.exe",
                        "exe": str(client_dir / "LeagueClientUx.exe"),
                    }
                },
            )()

            with patch(
                "injection.game.game_detector.psutil.process_iter",
                return_value=[process],
            ):
                game_path, client_path = detector.detect_paths()

        self.assertEqual(game_path, game_dir)
        self.assertEqual(client_path, client_dir)
        self.assertEqual(config.saved_paths, (str(game_dir), str(client_dir)))


if __name__ == "__main__":
    unittest.main()
