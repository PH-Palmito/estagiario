import unittest

from core.golden_commands import GOLDEN_COMMANDS_V1, golden_command_count
from core.normalizer import normalize_action
from core.router import route
from core.validator import validate_command


class GoldenCommandsV1Tests(unittest.TestCase):
    def test_v1_has_exactly_20_commands(self):
        self.assertEqual(golden_command_count(), 20)

    def test_ids_are_unique(self):
        ids = [item["id"] for item in GOLDEN_COMMANDS_V1]
        self.assertEqual(len(ids), len(set(ids)))

    def test_commands_route_normalize_validate_and_match_contract(self):
        for item in GOLDEN_COMMANDS_V1:
            with self.subTest(command=item["id"]):
                command = normalize_action(route(item["phrase"]))
                ok, error = validate_command(command)

                self.assertTrue(ok, error)
                self.assertEqual(command.action, item["expected_action"])
                self.assertEqual(command.requires_confirmation, item["requires_confirmation"])
                for key, value in item["expected_params"].items():
                    self.assertEqual(command.params.get(key), value)


if __name__ == "__main__":
    unittest.main()
