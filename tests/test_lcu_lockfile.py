import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lcu.core.lcu_connection import LCUConnection
from lcu.core.lockfile import Lockfile, find_lcu_credentials, parse_lockfile


class FakeProcess:
    def __init__(self, info):
        self.info = info


class LCUCredentialFallbackTests(unittest.TestCase):
    def setUp(self):
        self.wegame_process = FakeProcess(
            {
                "name": "LeagueClientUx.exe",
                "pid": 24696,
                "cmdline": [
                    "--app-port=9615",
                    "--remoting-auth-token=wegame-lcu-token",
                    "--region=TENCENT",
                ],
            }
        )

    def test_finds_lcu_credentials_from_wegame_client_arguments(self):
        credentials = find_lcu_credentials([self.wegame_process])

        self.assertEqual(
            credentials,
            Lockfile(
                name="LeagueClient",
                pid=24696,
                port=9615,
                password="wegame-lcu-token",
                protocol="https",
            ),
        )

    def test_empty_lockfile_falls_back_to_wegame_client_credentials(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            lockfile = Path(temp_dir) / "lockfile"
            lockfile.touch()

            credentials = parse_lockfile(
                str(lockfile),
                processes=[self.wegame_process],
            )

        self.assertEqual(credentials.port, 9615)
        self.assertEqual(credentials.password, "wegame-lcu-token")

    def test_valid_lockfile_remains_preferred_over_process_credentials(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            lockfile = Path(temp_dir) / "lockfile"
            lockfile.write_text(
                "LeagueClient:1234:2999:standard-lockfile-token:https",
                encoding="utf-8",
            )

            credentials = parse_lockfile(
                str(lockfile),
                processes=[self.wegame_process],
            )

        self.assertEqual(credentials.port, 2999)
        self.assertEqual(credentials.password, "standard-lockfile-token")

    def test_connection_uses_process_credentials_when_no_lockfile_exists(self):
        credentials = Lockfile(
            name="LeagueClient",
            pid=24696,
            port=9615,
            password="wegame-lcu-token",
            protocol="https",
        )

        with patch("lcu.core.lcu_connection.find_lockfile", return_value=None), patch(
            "lcu.core.lcu_connection.parse_lockfile", return_value=credentials
        ):
            connection = LCUConnection()

        self.assertTrue(connection.ok)
        self.assertEqual(connection.websocket_credentials(), (9615, "wegame-lcu-token"))


if __name__ == "__main__":
    unittest.main()
