class RuntimeState:
    def __init__(self):
        self.last_file = None
        self.last_folder = None
        self.last_app = None
        self.last_surface = None
        self.last_action = None
        self.last_result = None
        self.last_clipboard = None
        self.last_command = None
        self.axel_brain_plan = {}
        self.axel_brain_brief = {}
        self.axel_brain_contract = {}
        self.axel_brain_history = []
        self.last_route_trace = {}
        self.turns_since_long_memory_curated = 0
        self.last_long_memory_curated_at = 0.0

    def update(self, command, result):
        a = command.action
        p = command.params

        if a in {"file_create", "file_write", "file_append", "file_read"}:
            self.last_file = p.get("path")

        elif a in {"file_copy", "file_move"}:
            self.last_file = p.get("dst")

        elif a == "file_rename":
            self.last_file = p.get("new_name")

        elif a == "folder_create":
            self.last_folder = p.get("path")

        elif a in {"open_app", "close_app", "smart_close_app", "focus_app", "minimize_app", "maximize_app", "restore_app"}:
            self.last_app = p.get("target")
            self.last_surface = "app"

        elif a == "smart_open_choice":
            self.last_app = p.get("target")
            self.last_surface = "app" if p.get("kind") == "app" else "browser"

        elif a == "smart_open":
            result_text = str(result or "").lower()
            self.last_app = p.get("target")
            self.last_surface = "browser" if "site" in result_text else "app"

        elif a in {
            "open_url",
            "browser_new_tab",
            "browser_close_tab",
            "browser_next_tab",
            "browser_prev_tab",
            "browser_back",
            "browser_forward",
            "browser_refresh",
            "browser_open_first_result",
            "browser_open_focused_item",
            "browser_click_center",
            "browser_search",
            "browser_find",
            "browser_scroll_down",
            "browser_scroll_up",
            "browser_scroll_top",
            "browser_scroll_bottom",
            "browser_search_site",
            "browser_zoom_in",
            "browser_zoom_out",
            "browser_zoom_reset",
            "web_google_search",
            "web_open_chatgpt",
        }:
            self.last_app = "chrome"
            self.last_surface = "browser"

        self.last_action = a
        self.last_result = result

        if a != "respond":
            self.last_command = command

    def record_axel_brain_decision(self, plan: dict, contract: dict, route_trace: dict, *, limit: int = 12):
        entry = {
            "intent": str((plan or {}).get("intent") or (contract or {}).get("intent") or ""),
            "agent": str((plan or {}).get("agent") or ""),
            "toolset": str((plan or {}).get("toolset") or ""),
            "risk_level": str((plan or {}).get("risk_level") or ""),
            "channel": str((contract or {}).get("channel") or ""),
            "safety_profile": str(((contract or {}).get("remote_policy") or {}).get("safety_profile") or ""),
            "route_group": str((route_trace or {}).get("group") or ""),
            "detector": str((route_trace or {}).get("detector") or ""),
        }
        self.axel_brain_history.append(entry)
        if len(self.axel_brain_history) > limit:
            self.axel_brain_history = self.axel_brain_history[-limit:]
        return entry

    def axel_brain_history_summary(self) -> dict:
        items = [item for item in self.axel_brain_history if isinstance(item, dict)]
        profiles = {}
        agents = {}
        for item in items:
            profile = str(item.get("safety_profile") or "").strip()
            agent = str(item.get("agent") or "").strip()
            if profile:
                profiles[profile] = profiles.get(profile, 0) + 1
            if agent:
                agents[agent] = agents.get(agent, 0) + 1
        return {
            "total": len(items),
            "remote": sum(1 for item in items if str(item.get("channel") or "") == "remote"),
            "remote_blocked": profiles.get("remote_blocked", 0),
            "profiles": profiles,
            "agents": agents,
            "recommendations": self._axel_brain_recommendations(items),
        }

    @staticmethod
    def _axel_brain_recommendations(items: list[dict]) -> list[str]:
        if not items:
            return ["acumular mais decisoes antes de ajustar o comportamento"]
        blocked = sum(1 for item in items if str(item.get("safety_profile") or "") == "remote_blocked")
        remote_light = sum(1 for item in items if str(item.get("safety_profile") or "") == "remote_light_media_confirmation")
        high_risk = sum(1 for item in items if str(item.get("risk_level") or "") in {"high", "critical"})
        read = sum(1 for item in items if str(item.get("risk_level") or "") == "read")
        recommendations = []
        if blocked:
            recommendations.append("manter bloqueio remoto ampliado")
        if remote_light >= 2:
            recommendations.append("preservar botoes para midia remota")
        if high_risk:
            recommendations.append("auditar risco alto antes de ampliar")
        if read >= max(3, len(items) // 2):
            recommendations.append("otimizar leitura/cache")
        if not recommendations:
            recommendations.append("manter politica atual")
        return recommendations[:3]
