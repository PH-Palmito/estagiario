from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from tools.browser_screen_analysis import detect_screen_category, extract_finance_metrics
from tools.browser_screen_narrative import (
    explain_screen_lines,
    investment_screen_summary,
    should_auto_summarize,
    summarize_screen_lines,
)


@dataclass
class BrowserScreenCommands:
    activate_browser_window: Callable[[], bool]
    refresh_browser_context: Callable[[], str]
    get_browser_url: Callable[[], str]
    get_page_title: Callable[[], str]
    read_screen_content_lines: Callable[..., dict]
    clear_browser_snapshot: Callable[..., None]
    set_browser_elements: Callable[..., None]
    remember_text_items: Callable[..., None]
    remember_browser_analysis: Callable[..., None]
    screen_summary_intro: Callable[[], str]
    save_investment_snapshot: Callable[..., None]

    def summarize_screen(self) -> str:
        if not self.activate_browser_window():
            return "Nao encontrei um navegador aberto para resumir a tela."

        context, page_url, page_title, capture = self._capture(item_limit=10, page_limit=18)
        lines = capture["combined_lines"]
        if not lines:
            self.clear_browser_snapshot(context=context)
            return "Nao consegui resumir a tela atual."

        self._remember_capture(capture, lines, context=context)
        response = self.screen_summary_intro() + ": " + summarize_screen_lines(lines, page_url=page_url, page_title=page_title)
        self.remember_browser_analysis(response, lines=lines, page_url=page_url, page_title=page_title)
        return response

    def explain_screen(self) -> str:
        if not self.activate_browser_window():
            return "Nao encontrei um navegador aberto para detalhar a tela."

        context, page_url, page_title, capture = self._capture(item_limit=12, page_limit=22)
        lines = capture["combined_lines"]
        if not lines:
            self.clear_browser_snapshot(context=context)
            return "Nao consegui detalhar a tela atual."

        self._remember_capture(capture, lines, context=context)
        response = "Detalhando a tela: " + explain_screen_lines(lines, page_url=page_url, page_title=page_title)
        self.remember_browser_analysis(response, lines=lines, page_url=page_url, page_title=page_title)
        return response

    def investment_snapshot(self) -> str:
        if not self.activate_browser_window():
            return "Nao encontrei um navegador aberto para analisar investimentos."

        context, page_url, page_title, capture = self._capture(item_limit=14, page_limit=30)
        lines = capture["combined_lines"]
        if not lines:
            self.clear_browser_snapshot(context=context)
            return "Nao consegui ler dados financeiros uteis nessa tela."

        self._remember_capture(capture, lines, context=context)
        metrics = extract_finance_metrics(lines, limit=7)
        response = investment_screen_summary(lines, page_url=page_url, page_title=page_title)
        self.save_investment_snapshot(
            summary=response,
            metrics=metrics,
            lines=lines,
            page_url=page_url,
            page_title=page_title,
        )
        self.remember_browser_analysis(response, lines=lines, page_url=page_url, page_title=page_title, source="pagina financeira")
        return response

    def describe_screen(self) -> str:
        if not self.activate_browser_window():
            return "Nao encontrei um navegador aberto para ler a tela."

        context, page_url, page_title, capture = self._capture(item_limit=10, page_limit=18)
        items = capture["items"]
        lines = capture["combined_lines"]
        quality = capture["combined_quality"]
        category = detect_screen_category(lines, page_url=page_url, page_title=page_title)
        prefer_page_text = capture.get("prefer_page_text", False)

        if not lines:
            self.clear_browser_snapshot(context=context)
            return "Nao consegui ler itens clicaveis visiveis nessa tela."

        self._remember_capture(capture, lines, context=context)

        if category in {"repositorio github", "video youtube", "financas", "noticia"} or prefer_page_text:
            response = self.screen_summary_intro() + ": " + explain_screen_lines(lines, page_url=page_url, page_title=page_title)
            self.remember_browser_analysis(response, lines=lines, page_url=page_url, page_title=page_title)
            return response

        if should_auto_summarize(lines, quality, page_url=page_url, page_title=page_title):
            response = self.screen_summary_intro() + ": " + summarize_screen_lines(lines, page_url=page_url, page_title=page_title)
            self.remember_browser_analysis(response, lines=lines, page_url=page_url, page_title=page_title)
            return response

        if items:
            rows = [f"{idx}. {item['text']}" for idx, item in enumerate(items, start=1)]
        else:
            rows = [f"{idx}. {line}" for idx, line in enumerate(lines, start=1)]
        response = "Vejo na tela: " + "; ".join(rows)
        self.remember_browser_analysis(response, lines=lines, page_url=page_url, page_title=page_title)
        return response

    def _capture(self, item_limit: int, page_limit: int):
        context = self.refresh_browser_context()
        page_url = self.get_browser_url()
        page_title = self.get_page_title()
        capture = self.read_screen_content_lines(
            item_limit=item_limit,
            page_limit=page_limit,
            page_url=page_url,
            page_title=page_title,
        )
        return context, page_url, page_title, capture

    def _remember_capture(self, capture: dict, lines, context: str = ""):
        items = capture["items"]
        if items:
            self.set_browser_elements(items, context=context)
        else:
            self.remember_text_items(lines, context=context)
