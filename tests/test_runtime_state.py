import unittest

from core.command_schema import Command
from core.runtime_state import RuntimeState


class RuntimeStateTests(unittest.TestCase):
    def test_update_records_axel_brain_timeline_entry(self):
        state = RuntimeState()
        state.axel_brain_plan = {
            "intent": "close_app",
            "agent": "system_agent",
            "toolset": "sistema",
            "risk_level": "high",
            "needs_confirmation": True,
            "reason": "comando local de sistema",
            "confidence": 0.91,
            "response_mode": "execute_short",
            "model_policy": "local_first",
        }
        state.axel_brain_brief = {
            "memory_layers": [{"name": "memoria_curta"}, {"name": "skills_procedurais"}],
        }
        state.axel_brain_contract = {
            "source": "turn",
            "user_input": "fechar spotify",
            "channel": "local",
            "remote_policy": {"safety_profile": "local_normal"},
        }
        state.last_route_trace = {
            "source": "turn",
            "input": "fechar spotify",
            "intent": "close_app",
            "group": "system",
            "detector": "detect_close_app",
        }

        entry = state.update(
            Command(action="close_app", params={"target": "spotify"}, requires_confirmation=True),
            "Spotify fechado.",
        )

        self.assertIsNone(entry)
        self.assertEqual(len(state.axel_brain_timeline), 1)
        timeline_entry = state.axel_brain_timeline[0]
        self.assertEqual(timeline_entry["input"], "fechar spotify")
        self.assertEqual(timeline_entry["route_group"], "system")
        self.assertEqual(timeline_entry["detector"], "detect_close_app")
        self.assertEqual(timeline_entry["agent"], "system_agent")
        self.assertEqual(timeline_entry["toolset"], "sistema")
        self.assertTrue(timeline_entry["needs_confirmation"])
        self.assertEqual(timeline_entry["action"], "close_app")
        self.assertEqual(timeline_entry["params"], {"target": "spotify"})
        self.assertEqual(timeline_entry["result"], "Spotify fechado.")
        self.assertEqual(timeline_entry["decision"]["intent"], "close_app")
        self.assertEqual(timeline_entry["decision"]["reason"], "comando local de sistema")
        self.assertEqual(timeline_entry["decision"]["confidence"], 0.91)
        self.assertEqual(timeline_entry["context"]["memory_layers"], ["memoria_curta", "skills_procedurais"])
        self.assertEqual(timeline_entry["execution"]["action"], "close_app")
        self.assertTrue(timeline_entry["execution"]["needs_confirmation"])
        self.assertEqual(timeline_entry["response"]["final"], "Spotify fechado.")


if __name__ == "__main__":
    unittest.main()
