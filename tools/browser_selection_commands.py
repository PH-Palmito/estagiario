from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass


def build_translation_prompt(text: str, target_language: str = "portugues do Brasil") -> str:
    return f"""
Voce e um tradutor cuidadoso.
Traduza o texto abaixo para {target_language}.
Se o texto ja estiver em portugues, apenas corrija acentos e pequenos erros obvios sem inventar conteudo.
Responda somente com o texto final.
Nao escreva introducoes como "a traducao e".
Nao use aspas.

Texto:
{text}
""".strip()


def clean_translation_output(text: str):
    quote_chars = "\"' \u201c\u201d\u2018\u2019"
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    cleaned = cleaned.strip(quote_chars)

    prefix_patterns = [
        r"^(?:a\s+)?tradu[c\u00e7][a\u00e3]o\s+(?:do\s+texto\s+)?(?:para\s+portugu[e\u00ea]s(?:\s+do\s+brasil)?\s+)?(?:e|\u00e9|eh)\s*:?\s*",
        r"^em\s+portugu[e\u00ea]s(?:\s+do\s+brasil)?\s*:?\s*",
        r"^texto\s+traduzido\s*:?\s*",
        r"^traduzido\s*:?\s*",
    ]

    for pattern in prefix_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()

    return cleaned.strip(quote_chars)


@dataclass
class BrowserSelectionCommands:
    read_selected_text_from_browser: Callable[..., str | None]
    compact_selected_text: Callable[..., str]
    clear_browser_snapshot: Callable[..., None]
    set_last_selected_text: Callable[[str], None]
    last_selected_text: Callable[[], str]
    remember_browser_analysis: Callable[..., None]
    remember_text_items: Callable[..., None]
    selected_text_items: Callable[..., list[str]]
    ask_model: Callable[..., str]

    def read_selection(self) -> str:
        selected = self.read_selected_text_from_browser()
        if selected is None:
            return "Nao encontrei um navegador aberto para ler a selecao."

        text = self.compact_selected_text(selected)
        if not text:
            self.clear_browser_snapshot()
            self.set_last_selected_text("")
            return "Nao encontrei texto selecionado."

        self.clear_browser_snapshot()
        self.set_last_selected_text(text)
        response = "Texto selecionado: " + text
        self.remember_browser_analysis(response, lines=[text], source="texto selecionado")
        return response

    def translate_selection(self) -> str:
        selected = self.read_selected_text_from_browser()
        if selected is None:
            return "Nao encontrei um navegador aberto para traduzir a selecao."

        text = self.compact_selected_text(selected, max_length=1800)
        if not text:
            self.clear_browser_snapshot()
            return "Nao encontrei texto selecionado para traduzir."

        self.set_last_selected_text(text)
        return self._translate_text(text)

    def translate_last_selection(self) -> str:
        text = self.last_selected_text()
        if not text:
            return "Ainda nao tenho um texto guardado. Primeiro diga: ler selecionado."

        return self._translate_text(text)

    def read_selected_products(self) -> str:
        selected = self.read_selected_text_from_browser()
        if selected is None:
            return "Nao encontrei um navegador aberto para ler a selecao."

        self.set_last_selected_text(self.compact_selected_text(selected, max_length=1800))
        items = self.selected_text_items(selected, limit=10)
        if not items:
            self.clear_browser_snapshot()
            return "Nao consegui ler produtos no texto selecionado."

        self.remember_text_items(items)
        rows = [f"{idx}. {line}" for idx, line in enumerate(items, start=1)]
        response = "Li selecionado: " + "; ".join(rows)
        self.remember_browser_analysis(response, lines=items, source="texto selecionado")
        return response

    def translate_with_model(self, text: str, target_language: str = "portugues do Brasil") -> str:
        prompt = build_translation_prompt(text, target_language=target_language)
        return self.ask_model(
            prompt,
            timeout_seconds=20,
            num_predict=500,
            temperature=0.1,
        ).strip()

    def _translate_text(self, text: str) -> str:
        try:
            translated = self.translate_with_model(text)
        except Exception:
            return "Nao consegui traduzir agora. Verifique se o Ollama esta aberto."

        translated = self.compact_selected_text(clean_translation_output(translated), max_length=900)
        if not translated:
            return "Nao consegui gerar a traducao."

        self.clear_browser_snapshot()
        return "Traduzi: " + translated
