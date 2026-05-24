import unittest
from unittest.mock import patch

from core.codex_commands import (
    maybe_handle_codex_channel_command,
    maybe_handle_codex_implementation_request_command,
    maybe_handle_codex_inbox_command,
    maybe_handle_codex_outbox_command,
)


class CodexCommandTests(unittest.TestCase):
    def test_prepare_implementation_request_marks_handoff_started(self):
        with (
            patch(
                "core.codex_commands.save_codex_implementation_request",
                return_value={"status": "ready_for_codex", "title": "Extrair comandos"},
            ),
            patch("core.codex_commands.mark_handoff_started") as mark_started,
        ):
            result = maybe_handle_codex_implementation_request_command("preparar pedido de implementacao")

        mark_started.assert_called_once_with("pedido de implementacao preparado para o Codex")
        self.assertEqual(
            result,
            "Preparei o pedido de implementacao para o Codex: Extrair comandos. Deixei em memory/codex_implementation_request.md.",
        )

    def test_prepare_implementation_request_handles_blocked_state(self):
        with patch(
            "core.codex_commands.save_codex_implementation_request",
            return_value={"status": "blocked", "title": ""},
        ):
            result = maybe_handle_codex_implementation_request_command("gerar pedido de implementacao")

        self.assertEqual(result, "Ainda nao ha handoff pronto para transformar em pedido de implementacao ao Codex.")

    def test_show_implementation_request_formats_files(self):
        with patch(
            "core.codex_commands.load_codex_implementation_request",
            return_value={
                "status": "ready_for_codex",
                "title": "Extrair comandos",
                "files": ["main.py", "core/commands.py"],
            },
        ):
            result = maybe_handle_codex_implementation_request_command("mostrar pedido de implementacao")

        self.assertEqual(result, "Pedido pronto para Codex: Extrair comandos. Arquivos alvo: main.py, core/commands.py.")

    def test_enqueue_implementation_request_reports_pending_count(self):
        with (
            patch(
                "core.codex_commands.save_codex_implementation_request",
                return_value={"status": "ready_for_codex", "title": "Extrair comandos"},
            ),
            patch(
                "core.codex_commands.enqueue_codex_implementation_request",
                return_value={"pending": [{"title": "Extrair comandos"}, {"title": "Outro"}]},
            ),
            patch("core.codex_commands.mark_handoff_started") as mark_started,
        ):
            result = maybe_handle_codex_implementation_request_command("enviar pedido de implementacao")

        mark_started.assert_called_once_with("pedido de implementacao colocado na fila do Codex")
        self.assertEqual(result, "Pedido colocado na fila do Codex: Extrair comandos. Pendentes agora: 2.")

    def test_outbox_status_reports_pending_and_sent(self):
        with patch(
            "core.codex_commands.load_codex_outbox",
            return_value={"pending": [{"title": "Mensagem atual"}], "sent": [{"title": "Anterior"}]},
        ):
            result = maybe_handle_codex_outbox_command("fila do codex")

        self.assertEqual(result, "Fila do Codex: 1 pendente(s) e 1 entregue(s). Proxima mensagem: Mensagem atual.")

    def test_mark_implementation_request_sent_updates_handoff(self):
        with (
            patch(
                "core.codex_commands.load_codex_outbox",
                return_value={"pending": [{"title": "Pedido"}], "sent": []},
            ),
            patch(
                "core.codex_commands.mark_next_codex_message_sent",
                return_value={"pending": [], "sent": [{"kind": "implementation_request"}]},
            ),
            patch("core.codex_commands.mark_handoff_started") as mark_started,
        ):
            result = maybe_handle_codex_outbox_command("mensagem enviada ao codex")

        mark_started.assert_called_once_with("pedido de implementacao entregue ao Codex")
        self.assertEqual(result, "Registrei a entrega do pedido de implementacao ao Codex. Restam 0 pendente(s).")

    def test_inbox_status_reports_latest_item(self):
        with patch(
            "core.codex_commands.load_codex_inbox",
            return_value={"items": [{"kind": "reply", "text": "feito"}, {"kind": "decision", "text": "seguir"}]},
        ):
            result = maybe_handle_codex_inbox_command("inbox do codex")

        self.assertEqual(result, "Inbox do Codex: 2 resposta(s) registrada(s). Ultimo tipo: decision. Conteudo: seguir.")

    def test_register_codex_reply(self):
        with patch("core.codex_commands.add_codex_inbox_item") as add_item:
            result = maybe_handle_codex_inbox_command("codex respondeu revisei o patch")

        add_item.assert_called_once_with("reply", "revisei o patch")
        self.assertEqual(result, "Registrei a resposta do Codex na caixa de entrada do Axel.")

    def test_register_codex_applied_marks_handoff(self):
        with (
            patch("core.codex_commands.add_codex_inbox_item") as add_item,
            patch(
                "core.codex_commands.mark_handoff_applied",
                return_value={"handoff": {"title": "Extrair comandos"}},
            ) as mark_applied,
        ):
            result = maybe_handle_codex_inbox_command("codex aplicou ajuste no main")

        add_item.assert_called_once_with("implementation_applied", "ajuste no main")
        mark_applied.assert_called_once_with("ajuste no main")
        self.assertEqual(result, "Registrei que o Codex aplicou o handoff: Extrair comandos. Agora falta validar no uso real.")

    def test_prepare_codex_channel_reports_focus_and_status(self):
        with (
            patch(
                "core.codex_commands.save_codex_request",
                return_value={"title": "Melhorar voz"},
            ),
            patch(
                "core.codex_commands.save_codex_channel",
                return_value={"status": "ready"},
            ),
        ):
            result = maybe_handle_codex_channel_command("pedir melhoria ao codex")

        self.assertEqual(result, "Preparei um pedido ao Codex. Foco atual: Melhorar voz. Canal atual: ready.")

    def test_show_codex_channel_status(self):
        with patch(
            "core.codex_commands.load_codex_channel",
            return_value={
                "title": "Melhorar voz",
                "status": "ready",
                "urgency": "high",
                "next_action": "implementar",
            },
        ):
            result = maybe_handle_codex_channel_command("canal com codex")

        self.assertEqual(
            result,
            "Canal com o Codex: Melhorar voz. Estado: ready. Urgencia: high. Proxima acao: implementar.",
        )

    def test_codex_suggestion_prefers_consumed_message(self):
        with patch(
            "core.codex_commands.consume_codex_suggestion",
            return_value="Vale chamar o Codex agora.",
        ):
            result = maybe_handle_codex_channel_command("sugestao do codex")

        self.assertEqual(result, "Vale chamar o Codex agora.")

    def test_clear_codex_suggestion_memory(self):
        with patch("core.codex_commands.reset_codex_suggestion_memory") as reset:
            result = maybe_handle_codex_channel_command("limpar sugestao do codex")

        reset.assert_called_once_with()
        self.assertEqual(
            result,
            "Limpei a memoria da sugestao do Codex. O Axel pode avisar de novo no proximo ciclo forte.",
        )


if __name__ == "__main__":
    unittest.main()
