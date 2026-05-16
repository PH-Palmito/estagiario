import unittest
import inspect
import tempfile
from pathlib import Path
from unittest.mock import patch

from memory import investment_snapshot as inv


def fake_snapshot():
    return {
        "updated_at": 1_700_000_000,
        "summary": "Patrimonio R$ 10.000,00. Rentabilidade 12,00%.",
        "metric_map": {
            "patrimonio": "R$ 10.000,00",
            "rentabilidade": "12,00%",
        },
        "asset_positions": {
            "BBAS3": {
                "current_price": "R$ 30,00",
                "average_price": "R$ 20,00",
                "rentability": "50,00%",
                "variation": "1,20%",
                "balance": "R$ 3.000,00",
                "portfolio_percentage": "30,00%",
            },
            "PETR4": {
                "current_price": "R$ 35,00",
                "average_price": "R$ 28,00",
                "rentability": "25,00%",
                "variation": "-0,50%",
                "balance": "R$ 2.000,00",
                "portfolio_percentage": "20,00%",
            },
        },
        "asset_fundamentals": {
            "BBAS3": {
                "company_name": "Banco do Brasil",
                "quote": "R$ 30,00",
                "quote_value": 30.0,
                "dividend_yield_current": "8,00%",
                "dividend_yield_current_percent": 8.0,
                "next_dividend_events": [
                    {
                        "label": "JCP",
                        "rate": "R$ 0,50",
                        "payment_date": "2026-05-20",
                        "last_date_prior": "2026-05-10",
                    }
                ],
            },
            "PETR4": {
                "company_name": "Petrobras",
                "quote": "R$ 35,00",
                "quote_value": 35.0,
                "next_dividend_events": [
                    {
                        "label": "DIV",
                        "rate": "R$ 1,00",
                        "payment_date": "2026-06-15",
                        "last_date_prior": "2026-06-01",
                    }
                ],
            },
        },
    }


def fake_strategy(ticker: str):
    strategies = {
        "BBAS3": {
            "ticker": "BBAS3",
            "in_watchlist": True,
            "price_ceiling": 25.0,
            "thesis": "banco barato e pagador de dividendos",
            "auto_ceiling_enabled": True,
            "auto_ceiling_margin_percent": 8.0,
            "auto_ceiling_target_yield_percent": 8.0,
            "auto_ceiling_reference": "preco_medio",
        },
        "PETR4": {
            "ticker": "PETR4",
            "in_watchlist": False,
            "price_ceiling": None,
            "thesis": "",
            "auto_ceiling_enabled": True,
            "auto_ceiling_margin_percent": 8.0,
            "auto_ceiling_target_yield_percent": 8.0,
            "auto_ceiling_reference": "preco_medio",
        },
    }
    return strategies.get(str(ticker).upper(), {})


class InvestmentSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = fake_snapshot()

    def test_upcoming_dividend_brief_uses_snapshot_events(self):
        with patch.object(inv, "load_investment_snapshot", return_value=self.snapshot):
            result = inv.format_upcoming_dividend_brief(limit=2)

        self.assertIn("Dividendos", result)
        self.assertIn("BBAS3 paga JCP em 20/05", result)
        self.assertIn("PETR4 paga DIV em 15/06", result)

    def test_dividend_question_returns_portfolio_schedule(self):
        with patch.object(inv, "load_investment_snapshot", return_value=self.snapshot):
            result = inv.answer_investment_snapshot_question("agenda de dividendos")

        self.assertIn("Agenda de dividendos da carteira", result)
        self.assertIn("BBAS3", result)
        self.assertIn("pagamento em 20/05", result)

    def test_ticker_dividend_question_returns_ticker_events(self):
        with patch.object(inv, "load_investment_snapshot", return_value=self.snapshot):
            result = inv.answer_investment_snapshot_question("proximos dividendos de BBAS3")

        self.assertIn("BBAS3", result)
        self.assertIn("valor de R$ 0,50 por cota", result)

    def test_price_ceiling_question_uses_saved_strategy(self):
        with patch.object(inv, "load_investment_snapshot", return_value=self.snapshot), patch.object(inv, "get_asset_strategy", side_effect=fake_strategy):
            result = inv.answer_investment_snapshot_question("preco teto de BBAS3")

        self.assertIn("preço-teto salvo para BBAS3", result)
        self.assertIn("R$ 25,00", result)
        self.assertIn("acima", result)

    def test_assets_above_price_ceiling_are_reported(self):
        with patch.object(inv, "load_investment_snapshot", return_value=self.snapshot), patch.object(inv, "get_asset_strategy", side_effect=fake_strategy):
            result = inv.answer_investment_snapshot_question("quais ativos acima do meu preco teto")

        self.assertIn("BBAS3", result)
        self.assertIn("acima", result)

    def test_ticker_quote_average_and_trend_questions(self):
        with patch.object(inv, "load_investment_snapshot", return_value=self.snapshot):
            quote = inv.answer_investment_snapshot_question("cotacao de BBAS3")
            average = inv.answer_investment_snapshot_question("preco medio de BBAS3")
            trend = inv.answer_investment_snapshot_question("BBAS3 esta subindo")

        self.assertIn("R$ 30,00", quote)
        self.assertIn("R$ 20,00", average)
        self.assertIn("alta", trend)

    def test_ticker_yield_question_uses_fundamentals(self):
        with patch.object(inv, "load_investment_snapshot", return_value=self.snapshot):
            result = inv.answer_investment_snapshot_question("DY de BBAS3")

        self.assertIn("8,00%", result)

    def test_base_metric_negative_and_attention_questions(self):
        snapshot = fake_snapshot()
        snapshot["asset_positions"]["PETR4"]["rentability"] = "-5,00%"

        with patch.object(inv, "load_investment_snapshot", return_value=snapshot), patch.object(inv, "get_asset_strategy", side_effect=fake_strategy):
            patrimonio = inv.answer_investment_snapshot_question("qual o patrimonio")
            negativos = inv.answer_investment_snapshot_question("quais ativos negativos")
            attention = inv.answer_investment_snapshot_question("quais ativos merecem atencao")

        self.assertIn("R$ 10.000,00", patrimonio)
        self.assertIn("PETR4", negativos)
        self.assertIn("BBAS3", attention)

    def test_base_strategy_status_questions(self):
        with patch.object(inv, "load_investment_snapshot", return_value=self.snapshot), patch.object(inv, "get_asset_strategy", side_effect=fake_strategy):
            watchlist = inv.answer_investment_snapshot_question("BBAS3 esta na watchlist")
            thesis = inv.answer_investment_snapshot_question("qual tese de BBAS3")
            updated = inv.answer_investment_snapshot_question("quando a carteira foi atualizada")

        self.assertIn("watchlist", watchlist)
        self.assertIn("banco barato", thesis)
        self.assertIn("atualizada", updated)

    def test_auto_ceiling_settings_question(self):
        with patch.object(inv, "load_investment_snapshot", return_value=self.snapshot), patch.object(inv, "get_auto_ceiling_settings", return_value={"target_yield_percent": 8.0, "margin_percent": 10.0, "reference": "preco_medio"}):
            result = inv.answer_investment_snapshot_question("qual margem de seguranca")

        self.assertIn("8,0%", result)
        self.assertIn("10,0%", result)

    def test_grounded_investment_reading_skips_without_api_key(self):
        with patch.object(inv, "GEMINI_API_KEY", ""), patch.object(inv, "ask_gemini_grounded_model") as ask_model:
            result = inv._ask_grounded_investment_reading("analise BBAS3", self.snapshot)

        self.assertIsNone(result)
        ask_model.assert_not_called()

    def test_asset_news_answer_prefers_api_summary(self):
        with patch.object(inv, "get_asset_strategy", side_effect=fake_strategy), patch.object(inv, "summarize_asset_news", return_value="Resultado forte com dividendos maiores."), patch.object(inv, "_ask_grounded_asset_news") as grounded:
            result = inv._asset_news_answer("noticias de BBAS3", "BBAS3", self.snapshot, self.snapshot["asset_fundamentals"]["BBAS3"])

        self.assertEqual(result, "Resultado forte com dividendos maiores.")
        grounded.assert_not_called()

    def test_portfolio_items_above_ceiling_are_sorted_by_premium(self):
        snapshot = fake_snapshot()
        snapshot["asset_positions"]["VALE3"] = {
            "current_price": "R$ 60,00",
            "average_price": "R$ 55,00",
            "balance": "R$ 1.000,00",
            "portfolio_percentage": "10,00%",
        }

        def strategy_with_vale(ticker: str):
            if ticker == "VALE3":
                return {
                    "ticker": "VALE3",
                    "price_ceiling": 40.0,
                    "auto_ceiling_enabled": True,
                }
            return fake_strategy(ticker)

        with patch.object(inv, "get_asset_strategy", side_effect=strategy_with_vale):
            result = inv._portfolio_items_above_ceiling(snapshot)

        self.assertEqual([item["ticker"] for item in result[:3]], ["VALE3", "PETR4", "BBAS3"])

    def test_attention_items_handle_no_with_and_without_accent(self):
        snapshot = {
            "asset_positions": {
                "BBAS3": {
                    "current_price": "R$ 18,00",
                    "average_price": "R$ 20,00",
                    "buy_more": "nao",
                }
            }
        }

        with patch.object(inv, "get_asset_strategy", return_value={"auto_ceiling_enabled": False}):
            result = inv._portfolio_attention_items(snapshot)

        self.assertEqual(result[0]["ticker"], "BBAS3")
        self.assertIn("abaixo", result[0]["reasons"][0])

    def test_external_asset_reading_uses_strategy_context(self):
        fundamentals = {
            "company_name": "Banco do Brasil",
            "quote": "R$ 30,00",
            "quote_value": 30.0,
            "dividend_yield_current": "8,00%",
            "p_vp": "0,90",
        }

        with patch.object(inv, "get_asset_strategy", side_effect=fake_strategy):
            result = inv._format_external_asset_reading("BBAS3", fundamentals)

        self.assertIn("BBAS3", result)
        self.assertIn("R$ 25,00", result)
        self.assertIn("watchlist", result)

    def test_position_reading_includes_strategy_and_stance(self):
        snapshot = fake_snapshot()

        with patch.object(inv, "get_asset_strategy", side_effect=fake_strategy):
            result = inv._format_position_reading(snapshot, "BBAS3", snapshot["asset_positions"]["BBAS3"])

        self.assertIn("cotação atual", result)
        self.assertIn("preço-teto salvo", result)
        self.assertIn("watchlist", result)
        self.assertIn("observar", result)

    def test_local_investment_reading_mentions_snapshot_context(self):
        snapshot = fake_snapshot()
        snapshot["page_title"] = "BBAS3"

        with patch.object(inv, "get_asset_strategy", side_effect=fake_strategy):
            result = inv._build_local_investment_reading("BBAS3 esta caro?", snapshot)

        self.assertIn("BBAS3", result)
        self.assertIn("preço-teto", result)
        self.assertIn("barato ou caro", result)

    def test_metric_map_extracts_common_wallet_labels(self):
        result = inv._extract_metric_map(
            ["Patrimônio total R$ 10.000,00", "Rentabilidade 12,00%"],
            ["Proventos R$ 633,63"],
        )

        self.assertEqual(result["patrimonio"], "R$ 10.000,00")
        self.assertEqual(result["rentabilidade"], "12,00%")
        self.assertEqual(result["proventos"], "R$ 633,63")

    def test_save_snapshot_merges_partial_capture_positions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "investment_snapshot.json"
            original_path = inv.INVESTMENT_SNAPSHOT_PATH
            current_payload = {
                "asset_positions": {
                    "BBAS3": {"balance": "R$ 3.000,00"},
                    "PETR4": {"balance": "R$ 2.000,00"},
                },
                "asset_fundamentals": {"PETR4": {"company_name": "Petrobras"}},
            }
            inv._save_json(path, current_payload)

            try:
                inv.INVESTMENT_SNAPSHOT_PATH = path
                with patch.object(inv, "sync_portfolio_snapshot_note"):
                    result = inv.save_investment_snapshot(
                        "Resumo",
                        extra={
                            "asset_positions": {"BBAS3": {"balance": "R$ 3.100,00"}},
                            "asset_fundamentals": {"BBAS3": {"company_name": "Banco do Brasil"}},
                            "unresolved_category_counts": {"Acoes": {"reported": 2, "captured": 1}},
                        },
                    )
            finally:
                inv.INVESTMENT_SNAPSHOT_PATH = original_path

        self.assertTrue(result["partial_capture_merged"])
        self.assertIn("PETR4", result["asset_positions"])
        self.assertEqual(result["asset_positions"]["BBAS3"]["balance"], "R$ 3.100,00")

    def test_news_fingerprint_normalizes_accents_and_case(self):
        first = inv._news_fingerprint("Notícia Forte: Lucro subiu")
        second = inv._news_fingerprint("noticia forte lucro subiu")

        self.assertEqual(first, second)
        self.assertTrue(first)

    def test_signal_filter_skips_seen_and_marks_new_items(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "investment_signal_seen.json"
            original_path = inv.INVESTMENT_SIGNAL_SEEN_PATH
            inv._save_json(path, {"attention": [inv._signal_fingerprint("attention", "BBAS3 acima do teto")]})
            try:
                inv.INVESTMENT_SIGNAL_SEEN_PATH = path
                result = inv._filter_new_signal_texts(
                    "attention",
                    ["BBAS3 acima do teto", "PETR4 queda recente"],
                    only_new=True,
                    mark_seen=True,
                )
                saved = inv._load_json(path)
            finally:
                inv.INVESTMENT_SIGNAL_SEEN_PATH = original_path

        self.assertEqual(result, ["PETR4 queda recente"])
        self.assertIn(inv._signal_fingerprint("attention", "PETR4 queda recente"), saved["attention"])

    def test_financial_report_uses_summary_and_alert_sections(self):
        snapshot = fake_snapshot()
        snapshot["category_breakdown"] = {"Acoes": "70,00%", "FIIs": "30,00%"}

        with patch.object(inv, "load_investment_snapshot", return_value=snapshot), patch.object(inv, "get_asset_strategy", side_effect=fake_strategy), patch.object(inv, "_filter_new_signal_texts", side_effect=lambda _kind, texts, **_kwargs: texts), patch.object(inv, "_material_price_ceiling_items", side_effect=lambda items, **_kwargs: items), patch.object(inv, "_portfolio_news_digest", return_value=[]):
            result = inv.format_investment_financial_report()

        self.assertIn("Relatório financeiro", result)
        self.assertIn("Resumo:", result)
        self.assertIn("Alocação atual", result)
        self.assertIn("Preço-teto", result)

    def test_monitor_digest_returns_compact_signal_sections(self):
        snapshot = fake_snapshot()

        with patch.object(inv, "get_asset_strategy", side_effect=fake_strategy), patch.object(inv, "_filter_new_signal_texts", side_effect=lambda _kind, texts, **_kwargs: texts), patch.object(inv, "_material_price_ceiling_items", side_effect=lambda items, **_kwargs: items), patch.object(inv, "_portfolio_news_digest", return_value=["BBAS3: Resultado forte."]):
            result = inv._portfolio_monitor_digest(snapshot)

        self.assertIn("Monitoramento atual da carteira", result)
        self.assertIn("Preço-teto", result)
        self.assertIn("Notícia que merece radar", result)

    def test_portfolio_news_digest_filters_relevant_news_without_marking_seen(self):
        with patch.object(inv, "get_asset_strategy", side_effect=fake_strategy), patch.object(inv, "summarize_asset_news", return_value="Resultado forte com lucro e dividendos maiores."):
            result = inv._portfolio_news_digest(self.snapshot, limit_assets=2, limit_summaries=1, only_new=False, mark_seen=False)

        self.assertEqual(result, ["BBAS3: Resultado forte com lucro e dividendos maiores."])

    def test_news_question_uses_digest_without_external_state_when_patched(self):
        with patch.object(inv, "load_investment_snapshot", return_value=self.snapshot), patch.object(inv, "get_asset_strategy", side_effect=fake_strategy), patch.object(inv, "summarize_asset_news", return_value="Resultado forte com lucro e dividendos maiores."), patch.object(inv, "_news_seen_state", return_value={}), patch.object(inv, "_save_news_seen_state") as save_seen:
            result = inv.answer_investment_snapshot_question("tem noticias da carteira")

        self.assertIn("Noticias novas", result)
        self.assertIn("BBAS3", result)
        save_seen.assert_called_once()

    def test_fii_dy_answer_reports_weighted_average(self):
        snapshot = {
            "asset_positions": {
                "XPML11": {"portfolio_percentage": "30,00%", "balance": "R$ 3.000,00"},
                "VGIA11": {"portfolio_percentage": "10,00%", "balance": "R$ 1.000,00"},
            },
            "asset_fundamentals": {
                "XPML11": {
                    "company_name": "FII XP Malls",
                    "dividend_yield_current": "10,00%",
                    "dividend_yield_current_percent": 10.0,
                },
                "VGIA11": {
                    "company_name": "FII VGIA",
                    "dividend_yield_current": "14,00%",
                    "dividend_yield_current_percent": 14.0,
                },
            },
        }

        result = inv._portfolio_fii_dy_answer(snapshot)

        self.assertIn("XPML11 em 10,00%", result)
        self.assertIn("VGIA11 em 14,00%", result)
        self.assertIn("11,00%", result)

    def test_fii_dy_answer_explains_aggregated_private_wallet_gap(self):
        snapshot = {
            "source": "investidor10_private_wallet",
            "asset_positions": {},
            "category_breakdown": {"FIIs": "25,00%"},
            "unresolved_category_counts": {"FIIs": {"reported": 8, "captured": 2}},
        }

        result = inv._portfolio_fii_dy_answer(snapshot)

        self.assertIn("carteira privada", result)
        self.assertIn("8 ativos", result)
        self.assertIn("individualizar 2", result)

    def test_fii_dy_answer_has_single_definition(self):
        source = inspect.getsource(inv)
        self.assertEqual(source.count("def _portfolio_fii_dy_answer("), 1)


if __name__ == "__main__":
    unittest.main()
