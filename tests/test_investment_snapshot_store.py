import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory.investment_snapshot_store import save_investment_snapshot_payload


class InvestmentSnapshotStoreTests(unittest.TestCase):
    def test_save_snapshot_appends_daily_history(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_path = Path(temp_dir) / "investment_snapshot.json"

            with patch("memory.investment_snapshot_store.time.time", return_value=1780412294.0):
                save_investment_snapshot_payload(
                    snapshot_path,
                    summary="Carteira atualizada",
                    metrics=[],
                    lines=[],
                    extra={
                        "metric_map": {
                            "patrimonio": "R$ 7.983,36",
                            "rentabilidade": "11,94%",
                            "variacao": "-11.11%",
                        },
                        "asset_positions": {
                            "BTC": {
                                "category": "Criptos",
                                "balance": "R$ 1.000,00",
                            }
                        },
                    },
                    extract_metric_map=lambda _metrics, _lines: {},
                    sync_portfolio_snapshot_note=lambda _payload: None,
                )

            history = json.loads((Path(temp_dir) / "investment_snapshot_history.json").read_text(encoding="utf-8"))
            item = history["items"][0]

        self.assertEqual(item["date"], "2026-06-02")
        self.assertEqual(item["patrimonio_value"], 7983.36)
        self.assertEqual(item["rentabilidade_percent"], 11.94)
        self.assertEqual(item["crypto_balance_value"], 1000.0)


if __name__ == "__main__":
    unittest.main()
