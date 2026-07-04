import unittest

from core.router_investments import (
    detect_investment_browser_command,
    detect_investment_question_command,
    detect_investment_strategy_command,
)


class RouterInvestmentsTests(unittest.TestCase):
    def test_detects_refresh_wallet(self):
        self.assertEqual(
            detect_investment_browser_command("atualizar carteira"),
            {"intent": "investment_refresh_public_wallet", "target": None},
        )

    def test_detects_background_refresh_wallet(self):
        self.assertEqual(
            detect_investment_browser_command("atualizar carteira em segundo plano"),
            {"intent": "background_investment_refresh", "target": None},
        )

    def test_detects_wallet_summary(self):
        self.assertEqual(
            detect_investment_browser_command("minha carteira"),
            {"intent": "investment_memory_summary", "target": None},
        )

    def test_detects_open_wallet(self):
        self.assertEqual(
            detect_investment_browser_command("abrir carteira e resumir"),
            {"intent": "browser_open_wallet_and_summarize", "target": None},
        )

    def test_detects_investment_question(self):
        self.assertEqual(
            detect_investment_question_command("qual a cotacao de BBAS3"),
            {"intent": "investment_memory_answer", "target": "qual a cotacao de BBAS3"},
        )

    def test_detects_macro_climate_investment_questions(self):
        self.assertEqual(
            detect_investment_question_command("como o el nino afeta meus investimentos"),
            {"intent": "investment_memory_answer", "target": "como o el nino afeta meus investimentos"},
        )
        self.assertEqual(
            detect_investment_question_command("como o el nino afeta o VGIA11?"),
            {"intent": "investment_memory_answer", "target": "como o el nino afeta o VGIA11?"},
        )
        self.assertEqual(
            detect_investment_question_command("e o vgia como é afetado?"),
            {"intent": "investment_memory_answer", "target": "e o vgia como é afetado?"},
        )

    def test_detects_financial_report(self):
        self.assertEqual(
            detect_investment_question_command("relatorio financeiro"),
            {"intent": "investment_financial_report", "target": None},
        )

    def test_detects_daily_report(self):
        self.assertEqual(
            detect_investment_question_command("o que mudou na carteira desde ontem"),
            {"intent": "investment_daily_report", "target": None},
        )

    def test_detects_portfolio_monitor(self):
        self.assertEqual(
            detect_investment_question_command("monitor proativo da carteira"),
            {"intent": "investment_portfolio_monitor", "target": None},
        )

    def test_detects_background_financial_report(self):
        self.assertEqual(
            detect_investment_question_command("relatorio financeiro em segundo plano"),
            {"intent": "background_investment_report", "target": None},
        )

    def test_detects_price_ceiling(self):
        self.assertEqual(
            detect_investment_strategy_command("defina preco teto de BBAS3 em 25 reais"),
            {"intent": "investment_set_price_ceiling", "ticker": "BBAS3", "price": "25"},
        )

    def test_detects_watchlist_add_and_remove(self):
        self.assertEqual(
            detect_investment_strategy_command("adicione BBAS3 na watchlist"),
            {"intent": "investment_add_watchlist", "ticker": "BBAS3"},
        )
        self.assertEqual(
            detect_investment_strategy_command("remova BBAS3 da watchlist"),
            {"intent": "investment_remove_watchlist", "ticker": "BBAS3"},
        )

    def test_detects_thesis(self):
        self.assertEqual(
            detect_investment_strategy_command("salve tese de BBAS3 banco publico barato"),
            {"intent": "investment_set_thesis", "ticker": "BBAS3", "thesis": "banco publico barato"},
        )


if __name__ == "__main__":
    unittest.main()
