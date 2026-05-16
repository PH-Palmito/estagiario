import unittest
from unittest.mock import patch

from core.command_schema import Command
from core.executor import ACTIONS, execute
from core.normalizer import normalize_action
from core.router import route
from core.validator import validate_command
from actions import ActionSpec, ensure_default_actions, get_action, register_action


GOLDEN_COMMANDS = [
    ("briefing", "daily_briefing", {}),
    ("me da o briefing", "daily_briefing", {}),
    ("resumo do dia", "daily_briefing", {}),
    (
        "tem noticias da carteira",
        "investment_memory_answer",
        {"question": "tem noticias da carteira"},
    ),
    (
        "noticias da carteira",
        "investment_memory_answer",
        {"question": "noticias da carteira"},
    ),
    (
        "tem noticia sobre minha carteira",
        "investment_memory_answer",
        {"question": "tem noticia sobre minha carteira"},
    ),
    (
        "fatos relevantes da carteira",
        "investment_memory_answer",
        {"question": "fatos relevantes da carteira"},
    ),
    (
        "agenda de dividendos",
        "investment_memory_answer",
        {"question": "agenda de dividendos"},
    ),
    (
        "quais ativos acima do meu preco teto",
        "investment_memory_answer",
        {"question": "quais ativos acima do meu preco teto"},
    ),
    (
        "qual a cotacao de BBAS3",
        "investment_memory_answer",
        {"question": "qual a cotacao de BBAS3"},
    ),
    ("monitoramento da carteira", "investment_memory_answer", {"question": "monitoramento da carteira"}),
    ("radar da carteira", "investment_memory_answer", {"question": "radar da carteira"}),
    ("rentabilidade da carteira", "investment_memory_answer", {"question": "rentabilidade da carteira"}),
    ("quais ativos merecem atencao", "investment_memory_answer", {"question": "quais ativos merecem atencao"}),
    ("status do preco teto automatico", "investment_get_auto_ceiling_settings", {}),
    ("qual minha margem de seguranca", "investment_get_auto_ceiling_settings", {}),
    ("adicione BBAS3 na watchlist", "investment_add_watchlist", {"ticker": "BBAS3"}),
    ("remova BBAS3 da watchlist", "investment_remove_watchlist", {"ticker": "BBAS3"}),
    ("listar watchlist", "investment_list_watchlist", {}),
    (
        "defina preco teto de BBAS3 em 25 reais",
        "investment_set_price_ceiling",
        {"ticker": "BBAS3", "price": "25"},
    ),
    (
        "salve tese de BBAS3 banco publico barato",
        "investment_set_thesis",
        {"ticker": "BBAS3", "thesis": "banco publico barato"},
    ),
    ("abra o spotify", "open_app", {"target": "spotify"}),
    ("fecha spotify", "close_app", {"target": "spotify"}),
    ("foca no chrome", "focus_app", {"target": "chrome"}),
    ("minimize o chrome", "minimize_app", {"target": "chrome"}),
    ("abre https://example.com", "open_url", {"target": "https://example.com"}),
    ("clima em Salvador", "weather_summary", {"location": "Salvador"}),
    ("adicionar na agenda revisar Axel hoje", "agenda_add", {"text": "revisar Axel hoje"}),
    ("agenda de hoje", "agenda_list_today", {}),
    ("proximos compromissos", "agenda_list_all", {}),
    ("lembre de testar briefing amanha", "reminder_add", {"text": "testar briefing amanha"}),
    ("lembretes", "reminder_list", {}),
    (
        "lembre na memoria que briefing deve ser curto",
        "action_memory_remember",
        {"namespace": "investments", "key": "briefing_deve_ser_curto", "value": "briefing deve ser curto"},
    ),
    (
        "lembre que eu prefiro respostas curtas",
        "action_memory_remember",
        {"namespace": "preferences", "key": "respostas_curtas", "value": "respostas curtas"},
    ),
    (
        "o que voce sabe sobre briefing deve ser curto",
        "action_memory_recall",
        {"namespace": "investments", "key": "briefing_deve_ser_curto"},
    ),
    ("listar memoria investimentos", "action_memory_list", {"namespace": "investments"}),
    (
        'executar action file.process {"path":"README.md","max_chars":1000}',
        "action_tool_execute",
        {"name": "file.process", "arguments": {"path": "README.md", "max_chars": 1000}},
    ),
    (
        'executar action memory.remember {"namespace":"preferences","key":"tom","value":{"style":"curto"}}',
        "action_tool_execute",
        {"name": "memory.remember", "arguments": {"namespace": "preferences", "key": "tom", "value": {"style": "curto"}}},
    ),
    ("crie arquivo teste.txt", "file_create", {"path": "teste.txt"}),
    ("leia arquivo teste.txt", "file_read", {"path": "teste.txt"}),
    ("listar arquivos", "list_files", {"path": ""}),
    ("liste arquivos", "list_files", {"path": ""}),
    ("crie pasta relatórios", "folder_create", {"path": "relatórios"}),
    ("analise o codigo", "code_inspect_workspace", {}),
    ("inspecione o codigo", "code_inspect_workspace", {}),
    (
        "mostre o mapa de Salvador",
        "ui_show_map",
        {
            "target": {
                "kind": "place",
                "location": "Salvador",
                "label": "Salvador",
                "url": "https://www.google.com/maps/search/?api=1&query=Salvador",
            }
        },
    ),
    ("nova aba", "browser_new_tab", {}),
    ("fechar aba", "browser_close_tab", {}),
    ("role para baixo", "browser_scroll_down", {}),
    ("aumentar volume", "volume_up", {}),
    ("pausar musica", "media_play_pause", {}),
    ("ligar bluetooth", "bluetooth_on", {}),
    ("status do bluetooth", "bluetooth_status", {}),
    ("status da visao", "vision_status", {}),
    ("ultima analise visual", "vision_last_analysis", {}),
    ("historico visual", "vision_history", {}),
    ("analisar grafico", "image_analyze_screen_graph", {}),
    ("interpretar grafico", "image_analyze_screen_graph", {}),
    ("analisar grafico C:\\prints\\grafico.png", "image_analyze_graph", {"target": "C:\\prints\\grafico.png"}),
]


class GoldenCommandTests(unittest.TestCase):
    def test_golden_commands_route_normalize_and_validate(self):
        for phrase, expected_action, expected_params in GOLDEN_COMMANDS:
            with self.subTest(phrase=phrase):
                raw_action = route(phrase)
                command = normalize_action(raw_action)
                ok, error = validate_command(command)

                self.assertTrue(ok, error)
                self.assertEqual(command.action, expected_action)
                for key, value in expected_params.items():
                    self.assertEqual(command.params.get(key), value)

    def test_executor_actions_are_allowed_by_validator(self):
        ensure_default_actions()
        registered = {action.name for action in __import__("actions").list_actions()}
        missing = sorted(set(ACTIONS) - registered)
        self.assertEqual(missing, [])

    def test_executor_actions_are_registered_in_action_catalog(self):
        ensure_default_actions()
        registered = {action.name for action in __import__("actions").list_actions()}
        missing = sorted(set(ACTIONS) - registered)
        self.assertEqual(missing, [])

    def test_registered_action_tool_validation(self):
        ok, error = validate_command(
            Command(
                action="action_tool_execute",
                params={"name": "file.process", "arguments": {"path": "README.md"}},
            )
        )
        self.assertTrue(ok, error)

        ok, error = validate_command(
            Command(
                action="action_tool_execute",
                params={"name": "file.process", "arguments": {}},
            )
        )
        self.assertFalse(ok)
        self.assertIn("path", error)

        ok, error = validate_command(
            Command(
                action="action_tool_execute",
                params={"name": "unknown.tool", "arguments": {}},
            )
        )
        self.assertFalse(ok)
        self.assertIn("unknown.tool", error)

    def test_action_command_invalid_json_returns_friendly_response(self):
        command = normalize_action(route('executar action file.process {"path":'))
        self.assertEqual(command.action, "respond")
        self.assertIn("JSON de argumentos invalido", command.params.get("message", ""))

    def test_validate_command_uses_action_spec_for_regular_actions(self):
        ok, error = validate_command(Command(action="open_app", params={}))
        self.assertFalse(ok)
        self.assertEqual(error, "Qual alvo?")

        ok, error = validate_command(Command(action="open_app", params={"target": "spotify"}))
        self.assertTrue(ok, error)

    def test_legacy_read_actions_are_registered_as_read_only(self):
        ensure_default_actions()
        legacy_names = {
            "daily_briefing",
            "weather_summary",
            "windows_startup_status",
            "reminder_list",
            "agenda_list_today",
            "agenda_list_tomorrow",
            "agenda_list_all",
            "investment_memory_answer",
            "investment_memory_summary",
            "investment_financial_report",
            "investment_memory_status",
            "investment_list_watchlist",
            "investment_get_auto_ceiling_settings",
            "bluetooth_status",
            "vision_status",
            "vision_active_model",
            "vision_last_analysis",
            "vision_history",
            "list_files",
            "file_read",
            "action_tool_list",
            "action_tool_schema",
            "action_file_process",
            "action_memory_recall",
            "action_memory_list",
        }

        for name in legacy_names:
            with self.subTest(name=name):
                spec = get_action(name)
                self.assertIsNotNone(spec)
                self.assertTrue(spec.read_only)

    def test_legacy_read_action_required_params_are_validated(self):
        ok, error = validate_command(
            Command(
                action="action_tool_execute",
                params={"name": "investment_memory_answer", "arguments": {}},
            )
        )
        self.assertFalse(ok)
        self.assertIn("question", error)

        ok, error = validate_command(
            Command(
                action="action_tool_execute",
                params={"name": "investment_memory_answer", "arguments": {"question": "agenda de dividendos"}},
            )
        )
        self.assertTrue(ok, error)

    def test_legacy_write_actions_are_registered_with_confirmation(self):
        ensure_default_actions()
        write_names = {
            "agenda_add",
            "agenda_remove",
            "reminder_add",
            "reminder_remove",
            "action_memory_remember",
        }

        for name in write_names:
            with self.subTest(name=name):
                spec = get_action(name)
                self.assertIsNotNone(spec)
                self.assertFalse(spec.read_only)
                self.assertTrue(spec.requires_confirmation)

    def test_legacy_write_action_params_are_validated(self):
        ok, error = validate_command(
            Command(
                action="action_tool_execute",
                params={"name": "agenda_add", "arguments": {}},
            )
        )
        self.assertFalse(ok)
        self.assertIn("text", error)

        ok, error = validate_command(
            Command(
                action="action_tool_execute",
                params={"name": "agenda_add", "arguments": {"text": "hoje revisar Axel"}},
            )
        )
        self.assertTrue(ok, error)

    def test_action_tool_execute_inherits_confirmation_from_registry(self):
        command = normalize_action(
            {
                "intent": "action_tool_execute",
                "target": {"name": "agenda_add", "arguments": {"text": "hoje revisar Axel"}},
            }
        )
        self.assertTrue(command.requires_confirmation)

        command = normalize_action(
            {
                "intent": "action_tool_execute",
                "target": {"name": "daily_briefing", "arguments": {}},
            }
        )
        self.assertFalse(command.requires_confirmation)

    def test_investment_strategy_actions_require_confirmation(self):
        ensure_default_actions()
        strategy_names = {
            "investment.add_watchlist",
            "investment.remove_watchlist",
            "investment.set_price_ceiling",
            "investment.set_auto_ceiling_margin",
            "investment.set_thesis",
            "investment_refresh_public_wallet",
            "investment_add_watchlist",
            "investment_remove_watchlist",
            "investment_set_price_ceiling",
            "investment_set_auto_ceiling_margin",
            "investment_set_thesis",
        }

        for name in strategy_names:
            with self.subTest(name=name):
                spec = get_action(name)
                self.assertIsNotNone(spec)
                self.assertFalse(spec.read_only)
                self.assertTrue(spec.requires_confirmation)

    def test_investment_strategy_action_params_are_validated(self):
        ok, error = validate_command(
            Command(
                action="action_tool_execute",
                params={"name": "investment_set_price_ceiling", "arguments": {"ticker": "BBAS3"}},
            )
        )
        self.assertFalse(ok)
        self.assertIn("price", error)

        ok, error = validate_command(
            Command(
                action="action_tool_execute",
                params={"name": "investment_set_price_ceiling", "arguments": {"ticker": "BBAS3", "price": "25"}},
            )
        )
        self.assertTrue(ok, error)

    def test_action_tool_execute_inherits_investment_confirmation(self):
        command = normalize_action(
            {
                "intent": "action_tool_execute",
                "target": {"name": "investment_set_thesis", "arguments": {"ticker": "BBAS3", "thesis": "banco barato"}},
            }
        )
        self.assertTrue(command.requires_confirmation)

    def test_direct_investment_strategy_commands_require_confirmation(self):
        for phrase in [
            "adicione BBAS3 na watchlist",
            "remova BBAS3 da watchlist",
            "defina preco teto de BBAS3 em 25 reais",
            "salve tese de BBAS3 banco publico barato",
        ]:
            with self.subTest(phrase=phrase):
                command = normalize_action(route(phrase))
                self.assertTrue(command.requires_confirmation)

    def test_run_script_requires_confirmation(self):
        command = normalize_action(route("execute script teste.py"))
        self.assertEqual(command.action, "run_script")
        self.assertTrue(command.requires_confirmation)

    def test_sensitive_direct_commands_require_confirmation(self):
        phrase_cases = [
            ("fecha spotify", "close_app"),
            ("digite olá mundo", "type_text"),
            ("crie arquivo teste.txt", "file_create"),
            ("adicione no arquivo teste.txt: nova linha", "file_append"),
            ("copie origem.txt para destino.txt", "file_copy"),
            ("mova origem.txt para destino.txt", "file_move"),
            ("renomeie origem.txt para novo.txt", "file_rename"),
            ("crie pasta relatórios", "folder_create"),
        ]
        for phrase, expected_action in phrase_cases:
            with self.subTest(phrase=phrase):
                command = normalize_action(route(phrase))
                self.assertEqual(command.action, expected_action)
                self.assertTrue(command.requires_confirmation)

        raw_cases = [
            {"intent": "write_file", "target": "teste.txt", "content": "conteudo"},
            {"intent": "replace_in_file", "target": "teste.txt", "old_text": "a", "new_text": "b"},
            {"intent": "run_macro", "target": [{"intent": "daily_briefing"}]},
        ]
        for raw_action in raw_cases:
            with self.subTest(raw_action=raw_action):
                command = normalize_action(raw_action)
                self.assertTrue(command.requires_confirmation)

    def test_read_only_direct_commands_do_not_require_confirmation(self):
        for phrase in ["briefing", "leia arquivo teste.txt", "listar arquivos", "status do bluetooth"]:
            with self.subTest(phrase=phrase):
                command = normalize_action(route(phrase))
                self.assertFalse(command.requires_confirmation)

    def test_sensitive_legacy_actions_are_registered_with_confirmation(self):
        ensure_default_actions()
        sensitive_names = {
            "close_app",
            "run_script",
            "type_text",
            "file_create",
            "file_write",
            "file_append",
            "file_replace",
            "file_delete",
            "file_copy",
            "file_move",
            "file_rename",
            "folder_create",
        }

        for name in sensitive_names:
            with self.subTest(name=name):
                spec = get_action(name)
                self.assertIsNotNone(spec)
                self.assertFalse(spec.read_only)
                self.assertTrue(spec.requires_confirmation)

    def test_sensitive_legacy_action_params_are_validated(self):
        ok, error = validate_command(
            Command(
                action="action_tool_execute",
                params={"name": "file_write", "arguments": {"path": "teste.txt"}},
            )
        )
        self.assertFalse(ok)
        self.assertIn("content", error)

        ok, error = validate_command(
            Command(
                action="action_tool_execute",
                params={"name": "file_write", "arguments": {"path": "teste.txt", "content": "oi"}},
            )
        )
        self.assertTrue(ok, error)

    def test_registered_read_action_params_are_validated(self):
        ok, error = validate_command(
            Command(
                action="action_tool_execute",
                params={"name": "action_file_process", "arguments": {}},
            )
        )
        self.assertFalse(ok)
        self.assertIn("path", error)

        ok, error = validate_command(
            Command(
                action="action_tool_execute",
                params={"name": "action_memory_recall", "arguments": {"key": "preferencia"}},
            )
        )
        self.assertTrue(ok, error)

    def test_control_actions_are_registered_without_confirmation(self):
        ensure_default_actions()
        control_names = {
            "open_app",
            "focus_app",
            "minimize_app",
            "maximize_app",
            "restore_app",
            "open_url",
            "media_play_pause",
            "media_next",
            "media_previous",
            "media_play_pause_target",
            "media_play_target",
            "media_pause_target",
            "media_next_target",
            "media_previous_target",
            "volume_up",
            "volume_down",
            "volume_mute",
            "bluetooth_on",
            "bluetooth_off",
            "bluetooth_settings",
        }

        for name in control_names:
            with self.subTest(name=name):
                spec = get_action(name)
                self.assertIsNotNone(spec)
                self.assertFalse(spec.read_only)
                self.assertFalse(spec.requires_confirmation)

    def test_control_action_params_are_validated(self):
        ok, error = validate_command(
            Command(
                action="action_tool_execute",
                params={"name": "open_app", "arguments": {}},
            )
        )
        self.assertFalse(ok)
        self.assertIn("target", error)

        ok, error = validate_command(
            Command(
                action="action_tool_execute",
                params={"name": "open_app", "arguments": {"target": "spotify"}},
            )
        )
        self.assertTrue(ok, error)

    def test_browser_actions_are_registered(self):
        ensure_default_actions()
        browser_names = {
            "browser_new_tab",
            "browser_close_tab",
            "browser_back",
            "browser_forward",
            "browser_refresh",
            "browser_click_text",
            "browser_describe_screen",
            "browser_summarize_screen",
            "browser_search",
            "browser_find",
            "browser_scroll_down",
            "browser_zoom_in",
            "browser_search_site",
            "browser_search_music",
            "browser_music_session",
            "spotify_diagnostic",
            "spotify_like_current_track",
            "spotify_less_music_vibe",
        }

        for name in browser_names:
            with self.subTest(name=name):
                self.assertIsNotNone(get_action(name))

    def test_browser_action_params_are_validated(self):
        ok, error = validate_command(
            Command(
                action="action_tool_execute",
                params={"name": "browser_click_text", "arguments": {}},
            )
        )
        self.assertFalse(ok)
        self.assertIn("query", error)

        ok, error = validate_command(
            Command(
                action="action_tool_execute",
                params={"name": "browser_click_text", "arguments": {"query": "Comprar"}},
            )
        )
        self.assertTrue(ok, error)

    def test_browser_click_actions_require_confirmation(self):
        ensure_default_actions()
        for name in {"browser_close_tab", "browser_click_center", "browser_click_text", "browser_click_listed_item"}:
            with self.subTest(name=name):
                spec = get_action(name)
                self.assertIsNotNone(spec)
                self.assertTrue(spec.requires_confirmation)

    def test_misc_actions_are_registered(self):
        ensure_default_actions()
        names = {
            "respond",
            "start_conversation",
            "stop_conversation",
            "run_macro",
            "ui_show_map",
            "web_google_search",
            "web_open_chatgpt",
            "code_inspect_workspace",
            "code_inspect_target",
            "code_inspect_selection",
            "smart_open",
            "smart_open_choice",
            "remember_target_kind",
            "forget_smart_memory",
            "smart_close_app",
            "windows_startup_enable",
            "windows_startup_disable",
        }

        for name in names:
            with self.subTest(name=name):
                self.assertIsNotNone(get_action(name))

    def test_misc_sensitive_actions_require_confirmation(self):
        ensure_default_actions()
        for name in {"run_macro", "remember_target_kind", "forget_smart_memory", "smart_close_app", "windows_startup_enable", "windows_startup_disable"}:
            with self.subTest(name=name):
                spec = get_action(name)
                self.assertIsNotNone(spec)
                self.assertTrue(spec.requires_confirmation)

    def test_misc_action_params_are_validated(self):
        ok, error = validate_command(
            Command(
                action="action_tool_execute",
                params={"name": "web_google_search", "arguments": {}},
            )
        )
        self.assertFalse(ok)
        self.assertIn("query", error)

        ok, error = validate_command(
            Command(
                action="action_tool_execute",
                params={"name": "web_google_search", "arguments": {"query": "Axel"}},
            )
        )
        self.assertTrue(ok, error)

    def test_action_catalog_covers_executor_inventory(self):
        ensure_default_actions()
        registered = {action.name for action in __import__("actions").list_actions()}
        missing = sorted(set(ACTIONS) - registered)
        self.assertEqual(missing, [])

    def test_vision_actions_are_registered(self):
        ensure_default_actions()
        names = {
            "image_analyze",
            "image_analyze_graph",
            "image_analyze_screen",
            "image_analyze_screen_graph",
            "image_analyze_browser",
            "image_analyze_clipboard",
            "vision_answer_question",
            "vision_install_hint",
            "vision_download_light_model",
            "action_tool_execute",
        }

        for name in names:
            with self.subTest(name=name):
                self.assertIsNotNone(get_action(name))

    def test_vision_action_params_are_validated(self):
        ok, error = validate_command(
            Command(
                action="action_tool_execute",
                params={"name": "vision_answer_question", "arguments": {}},
            )
        )
        self.assertFalse(ok)
        self.assertIn("question", error)

        ok, error = validate_command(
            Command(
                action="action_tool_execute",
                params={"name": "vision_answer_question", "arguments": {"question": "o que tem na tela?"}},
            )
        )
        self.assertTrue(ok, error)

    def test_vision_download_requires_confirmation(self):
        ensure_default_actions()
        spec = get_action("vision_download_light_model")
        self.assertIsNotNone(spec)
        self.assertTrue(spec.requires_confirmation)

    def test_executor_uses_registered_action_before_legacy_table(self):
        register_action(
            ActionSpec(
                name="unit.echo",
                description="Action de teste.",
                handler=lambda args: f"echo:{args.get('value')}",
                parameters={"value": {"type": "string", "required": True}},
            )
        )

        result = execute(Command(action="unit.echo", params={"value": "ok"}))
        self.assertEqual(result, "echo:ok")

    def test_executor_rejects_unregistered_action(self):
        result = execute(Command(action="unit.missing", params={}))
        self.assertIn("Ação desconhecida", result)

    def test_action_tool_execute_does_not_call_itself_recursively(self):
        result = execute(Command(action="action_tool_execute", params={"name": "action_tool_execute", "arguments": {"name": "daily_briefing"}}))
        self.assertIn("Nao executo", result)

    def test_ui_show_map_registered_handler_updates_ui_state(self):
        payload = {"label": "Salvador", "location": "Salvador"}
        with patch("actions.legacy_misc_actions.update_ui_state") as update_mock:
            result = execute(Command(action="ui_show_map", params={"target": payload}))

        self.assertEqual(result, "Mapa aberto na interface: Salvador.")
        update_mock.assert_called_once()
        state = update_mock.call_args.args[0]
        self.assertTrue(state["visible"])
        self.assertTrue(state["map_panel_open"])
        self.assertEqual(state["map_request"], payload)


if __name__ == "__main__":
    unittest.main()
