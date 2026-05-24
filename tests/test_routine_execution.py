import unittest
from types import SimpleNamespace

from core.routine_execution import append_multi_step_result, execute_routine_steps, handle_multi_step_request


def route_step(step):
    return {"intent": "step", "target": step}


def execute_command(command):
    return f"executed:{command.action}"


class RoutineExecutionTests(unittest.TestCase):
    def test_append_multi_step_result_deduplicates_repeated_noise(self):
        results = ["Nao entendi."]

        append_multi_step_result(results, "Nao entendi.")
        append_multi_step_result(results, "Tudo certo.")

        self.assertEqual(results, ["Nao entendi.", "Tudo certo."])

    def test_multi_step_uses_local_split_before_planner(self):
        def split_local_steps(_text):
            return ["abrir chrome", "abrir spotify"]

        def process_action(raw_action):
            return SimpleNamespace(
                action=raw_action["target"],
                params={},
                requires_confirmation=False,
            )

        result = handle_multi_step_request(
            "abrir chrome e abrir spotify",
            split_local_steps=split_local_steps,
            plan_actions=lambda _text: self.fail("planner should not run"),
            route_step=route_step,
            process_action=process_action,
            execute_command=execute_command,
        )

        self.assertEqual(result, "executed:abrir chrome\nexecuted:abrir spotify")

    def test_multi_step_blocks_sensitive_command(self):
        def process_action(raw_action):
            if raw_action["target"] == "apague arquivo":
                return SimpleNamespace(action="delete_file", params={"path": "x"}, requires_confirmation=True)
            return SimpleNamespace(action="open_app", params={}, requires_confirmation=False)

        result = handle_multi_step_request(
            "apague arquivo e abra chrome",
            split_local_steps=lambda _text: ["apague arquivo", "abra chrome"],
            plan_actions=lambda _text: [],
            route_step=route_step,
            process_action=process_action,
            execute_command=execute_command,
        )

        self.assertEqual(
            result,
            "Acao sensivel no plano bloqueada: delete_file {'path': 'x'}\nexecuted:open_app",
        )

    def test_comma_without_local_steps_returns_none(self):
        result = handle_multi_step_request(
            "abrir chrome, talvez",
            split_local_steps=lambda _text: ["abrir chrome, talvez"],
            plan_actions=lambda _text: self.fail("planner should not run"),
            route_step=route_step,
            process_action=lambda _raw: "",
            execute_command=execute_command,
        )

        self.assertIsNone(result)

    def test_execute_routine_rejects_non_list(self):
        result = execute_routine_steps(
            "abrir chrome",
            route_step=route_step,
            process_action=lambda _raw: "",
            execute_command=execute_command,
        )

        self.assertEqual(result, "Rotina invalida.")

    def test_execute_routine_reports_invalid_and_sensitive_steps(self):
        def process_action(raw_action):
            if raw_action["target"] == "apagar":
                return SimpleNamespace(action="delete_file", params={}, requires_confirmation=True)
            return SimpleNamespace(action=raw_action["target"], params={}, requires_confirmation=False)

        result = execute_routine_steps(
            ["abrir", "", "apagar"],
            route_step=route_step,
            process_action=process_action,
            execute_command=execute_command,
        )

        self.assertEqual(result, "executed:abrir\nEtapa invalida na rotina.\nEtapa sensivel bloqueada: delete_file")


if __name__ == "__main__":
    unittest.main()
