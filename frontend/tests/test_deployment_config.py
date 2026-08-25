"""Keep frontend and backend demo limits aligned in deployment config."""

from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class DeploymentConfigTests(unittest.TestCase):
    def test_compose_and_example_env_use_the_adopted_live_demo_values(self):
        compose = (REPOSITORY_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        example_env = (REPOSITORY_ROOT / ".env.example").read_text(encoding="utf-8")

        self.assertIn(
            'STEELGUARD_USE_MOCK_API: "${STEELGUARD_USE_MOCK_API:-false}"',
            compose,
        )
        self.assertIn(
            'STEELGUARD_API_CONNECT_TIMEOUT_SECONDS: "${STEELGUARD_API_CONNECT_TIMEOUT_SECONDS:-2}"',
            compose,
        )
        self.assertIn(
            'STEELGUARD_API_READ_TIMEOUT_SECONDS: "${STEELGUARD_API_READ_TIMEOUT_SECONDS:-30}"',
            compose,
        )
        self.assertEqual(
            compose.count(
                'STEELGUARD_MAX_UPLOAD_BYTES: "${STEELGUARD_MAX_UPLOAD_BYTES:-1048576}"'
            ),
            2,
        )

        for setting in (
            "STEELGUARD_USE_MOCK_API=false",
            "STEELGUARD_API_CONNECT_TIMEOUT_SECONDS=2",
            "STEELGUARD_API_READ_TIMEOUT_SECONDS=30",
            "STEELGUARD_MAX_UPLOAD_BYTES=1048576",
            'STEELGUARD_RECOMMENDATION_MAP_JSON={"Crazing":"REJECT","Inclusion":"REJECT","Patches":"REWORK","Pitted Surface":"REJECT","Rolled-in Scale":"REWORK","Scratches":"REWORK"}',
        ):
            self.assertIn(setting, example_env)


if __name__ == "__main__":
    unittest.main()
