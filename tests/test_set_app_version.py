import unittest

from scripts.set_app_version import replace_app_version_text, validate_version


class SetAppVersionTests(unittest.TestCase):
    def test_replaces_app_version_assignment_only(self):
        text = (
            'APP_VERSION = "1.2.14"                          # Application version\n'
            'APP_USER_AGENT = f"Rose/{APP_VERSION}"\n'
        )

        updated = replace_app_version_text(text, "1.2.14.1")

        self.assertIn('APP_VERSION = "1.2.14.1"', updated)
        self.assertIn('APP_USER_AGENT = f"Rose/{APP_VERSION}"', updated)

    def test_rejects_suffix_versions(self):
        with self.assertRaises(ValueError):
            validate_version("1.2.14-cn.1")


if __name__ == "__main__":
    unittest.main()
