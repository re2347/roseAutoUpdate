import unittest

from scripts.publish_gitcode_release import PublishDecision, choose_publish_decision


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


if __name__ == "__main__":
    unittest.main()
